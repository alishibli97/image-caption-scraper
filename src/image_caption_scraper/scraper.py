"""Selenium-based image and caption scraper."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from html import unescape
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlencode, urlparse

import requests
from loguru import logger
from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from typing_extensions import Self

from .expansion import generate_synonyms, translate_query
from .helper import ScraperConfig, save_image

ENGINE_NAMES = ("google", "yahoo", "flickr")
GOOGLE_IMAGE_SELECTOR = "img.YQ4gaf, img.Q4LuWd"
GOOGLE_FULL_IMAGE_SELECTOR = "img.sFlh5c.iPVvYb, img.n3VNCb"
YAHOO_IMAGE_SELECTOR = "#sres li img, ul#sres img"
FLICKR_ITEM_SELECTOR = ".photo-list-photo-view img"


class SearchEngineAccessError(RuntimeError):
    """Raised when a search engine returns a block, challenge, or error page."""


class ImageCaptionScraper:
    """Download images and captions from supported image search engines."""

    def __init__(
        self,
        engine: str = "all",
        num_images: int = 100,
        query: str = "dog chases cat",
        out_dir: str | Path = "images",
        headless: bool = True,
        driver: str | None = "chromedriver",
        expand: bool = False,
        translate: bool = False,
        k: int = 3,
        collect_public_ip: bool = False,
        min_width: int = 128,
        min_height: int = 128,
    ) -> None:
        logger.info("Initializing scraper")
        self.cfg = ScraperConfig(
            engine,
            num_images,
            query,
            out_dir,
            headless,
            driver,
            expand,
            translate,
            k,
            min_width,
            min_height,
        )
        self.public_ip = self.get_public_ip_address() if collect_public_ip else None
        self._prepare_queries()
        self.wd: webdriver.Chrome | None = None
        self.start_web_driver()

    def _prepare_queries(self) -> None:
        if self.cfg.expand:
            expansions = generate_synonyms(self.cfg.query, self.cfg.k)
            for index, query in enumerate(expansions, start=1):
                self.cfg.queries[f"Expansion {index}"] = query

        if self.cfg.translate:
            try:
                from transformers import T5ForConditionalGeneration, T5Tokenizer
            except ImportError as exc:
                raise RuntimeError(
                    "Translation requires optional dependencies. Install them with: "
                    "pip install 'image-caption-scraper[translate]'"
                ) from exc

            tokenizer = T5Tokenizer.from_pretrained("t5-small")
            model = T5ForConditionalGeneration.from_pretrained("t5-small")
            self.cfg.queries.update(translate_query(tokenizer, model, self.cfg.query))

    def get_public_ip_address(self) -> str | None:
        """Return the public IP when explicitly requested, or ``None`` on failure."""

        try:
            response = requests.get("https://api.ipify.org", timeout=(3, 5))
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Could not determine public IP: {}", exc)
            return None
        return response.text.strip() or None

    def start_web_driver(self) -> None:
        """Start Chrome using Selenium Manager or an explicit driver path."""

        chrome_options = Options()
        if self.cfg.headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-dev-shm-usage")

        custom_driver = self.cfg.driver not in {None, "", "chromedriver"}
        if custom_driver:
            service = Service(executable_path=str(self.cfg.driver))
            self.wd = webdriver.Chrome(service=service, options=chrome_options)
        else:
            self.wd = webdriver.Chrome(options=chrome_options)

    def close(self) -> None:
        """Close the browser session. Calling this more than once is safe."""

        if self.wd is not None:
            try:
                self.wd.quit()
            finally:
                self.wd = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def scrape(
        self,
        save_images: bool = True,
        *,
        close_driver: bool = True,
    ) -> dict[str, dict[str, str | None]]:
        """Scrape data, save it, return it, and close the browser by default."""

        try:
            image_data = self.crawl()
            if save_images:
                return self.save_images_and_captions(image_data)
            self.save_images_data(image_data)
            return image_data
        finally:
            if close_driver:
                self.close()

    def crawl(self) -> dict[str, dict[str, str | None]]:
        """Collect exactly the requested maximum across selected engines."""

        engines = ENGINE_NAMES if self.cfg.engine == "all" else (self.cfg.engine,)
        base, remainder = divmod(self.cfg.num_images, len(engines))
        merged: dict[str, dict[str, str | None]] = {}
        seen_urls: set[str] = set()

        for index, engine in enumerate(engines):
            target = base + (1 if index < remainder else 0)
            if target == 0:
                continue
            method = getattr(self, f"get_{engine}_images")
            try:
                engine_data = method(limit=target)
            except (SearchEngineAccessError, WebDriverException):
                logger.exception("{} scraping failed", engine.capitalize())
                if len(engines) == 1:
                    raise
                continue

            for filename, item in engine_data.items():
                url = str(item["url"])
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                merged[filename] = item
                if len(merged) >= self.cfg.num_images:
                    return merged
        return merged

    def set_target_url(self, engine: str, query: str) -> str:
        """Build and store an encoded search URL."""

        url_index = {
            "google": f"https://www.google.com/search?{urlencode({'tbm': 'isch', 'q': query})}",
            "yahoo": f"https://images.search.yahoo.com/search/images?{urlencode({'p': query})}",
            "flickr": f"https://www.flickr.com/search/?{urlencode({'text': query})}",
        }
        try:
            self.target_url = url_index[engine]
        except KeyError as exc:
            raise ValueError(f"Unsupported engine: {engine}") from exc
        return self.target_url

    def _query_targets(self, limit: int) -> list[tuple[str, str, int]]:
        unique_queries = list(dict.fromkeys(self.cfg.queries.values()))
        base, remainder = divmod(limit, len(unique_queries))
        targets = []
        for index, query in enumerate(unique_queries):
            target = base + (1 if index < remainder else 0)
            if target:
                targets.append((f"Query {index + 1}", query, target))
        return targets

    def _image_source(self, element: object) -> str | None:
        data_url = None
        for attribute in ("src", "data-src", "data-original"):
            value = element.get_attribute(attribute)
            if value and value.startswith(("http://", "https://")):
                return value
            if value and value.startswith("//"):
                return f"https:{value}"
            if value and value.startswith("data:"):
                data_url = value
        return data_url

    def _image_dimensions(self, element: object) -> tuple[int, int]:
        assert self.wd is not None
        dimensions = self.wd.execute_script(
            "return [arguments[0].naturalWidth || 0, arguments[0].naturalHeight || 0];",
            element,
        )
        return int(dimensions[0]), int(dimensions[1])

    def _best_image_url(
        self,
        elements: list[object],
        *,
        excluded_urls: set[str] | None = None,
        rejected_hosts: tuple[str, ...] = (),
    ) -> str | None:
        excluded_urls = excluded_urls or set()
        candidates: list[tuple[int, str]] = []
        for element in elements:
            try:
                url = self._image_source(element)
                if not url or url in excluded_urls or not url.startswith(("http://", "https://")):
                    continue
                host = (urlparse(url).hostname or "").lower()
                if any(
                    host == rejected or host.endswith(f".{rejected}") for rejected in rejected_hosts
                ):
                    continue
                width, height = self._image_dimensions(element)
                if width < self.cfg.min_width or height < self.cfg.min_height:
                    continue
            except (StaleElementReferenceException, TypeError, ValueError):
                continue
            candidates.append((width * height, url))
        return max(candidates, default=(0, None))[1]

    def _google_full_image_url(self, thumbnail: object) -> str | None:
        assert self.wd is not None
        thumbnail_url = self._image_source(thumbnail)
        try:
            self.wd.execute_script("arguments[0].scrollIntoView({block: 'center'});", thumbnail)
            self.wd.execute_script("arguments[0].click();", thumbnail)
        except (StaleElementReferenceException, WebDriverException):
            return None

        def full_image_url(driver: webdriver.Chrome) -> str | None:
            candidates = driver.find_elements(By.CSS_SELECTOR, GOOGLE_FULL_IMAGE_SELECTOR)
            return self._best_image_url(
                candidates,
                excluded_urls={thumbnail_url} if thumbnail_url else set(),
                rejected_hosts=("gstatic.com",),
            )

        try:
            return WebDriverWait(self.wd, 3).until(full_image_url)
        except TimeoutException:
            return None

    @staticmethod
    def _url_from_yahoo_metadata(values: list[str]) -> str | None:
        preferred_keys = {"iurl", "imgurl", "imageurl", "mediaurl", "image_url"}

        def valid_url(value: object) -> str | None:
            if not isinstance(value, str):
                return None
            candidate = unquote(unescape(value)).replace("\\/", "/")
            return candidate if candidate.startswith(("http://", "https://")) else None

        def walk(value: object) -> str | None:
            if isinstance(value, dict):
                for key, item in value.items():
                    if key.lower() in preferred_keys and (candidate := valid_url(item)):
                        return candidate
                for item in value.values():
                    if candidate := walk(item):
                        return candidate
            elif isinstance(value, list):
                for item in value:
                    if candidate := walk(item):
                        return candidate
            return None

        for raw_value in values:
            parsed = urlparse(unescape(raw_value))
            for key, items in parse_qs(parsed.query).items():
                if key.lower() in preferred_keys:
                    for item in items:
                        if candidate := valid_url(item):
                            return candidate
            try:
                structured = json.loads(raw_value)
            except (json.JSONDecodeError, TypeError):
                continue
            if candidate := walk(structured):
                return candidate
        return None

    def _yahoo_full_image_url(self, thumbnail: object) -> str | None:
        assert self.wd is not None
        values = self.wd.execute_script(
            """
            const image = arguments[0];
            const item = image.closest('li');
            const link = image.closest('a') || (item && item.querySelector('a'));
            const nodes = [item, link].filter(Boolean);
            return nodes.flatMap(node => Array.from(node.attributes, attr => attr.value));
            """,
            thumbnail,
        )
        if original_url := self._url_from_yahoo_metadata(values or []):
            return original_url

        thumbnail_url = self._image_source(thumbnail)
        try:
            self.wd.execute_script("arguments[0].click();", thumbnail)
        except (StaleElementReferenceException, WebDriverException):
            return None

        def full_image_url(driver: webdriver.Chrome) -> str | None:
            return self._best_image_url(
                driver.find_elements(By.TAG_NAME, "img"),
                excluded_urls={thumbnail_url} if thumbnail_url else set(),
                rejected_hosts=("yimg.com",),
            )

        try:
            return WebDriverWait(self.wd, 3).until(full_image_url)
        except TimeoutException:
            return None

    @staticmethod
    def _flickr_large_image_url(url: str) -> str | None:
        host = (urlparse(url).hostname or "").lower()
        is_photo_host = host == "live.staticflickr.com" or bool(
            re.fullmatch(r"farm\d+\.staticflickr\.com", host)
        )
        if not is_photo_host:
            return None
        return re.sub(
            r"_(?:s|q|t|m|n|w|z|c)\.(jpe?g|png|gif)$",
            r"_b.\1",
            url,
            flags=re.IGNORECASE,
        )

    def _result(
        self,
        *,
        query: str,
        url: str,
        caption: str,
        source: str,
    ) -> tuple[str, dict[str, str | None]]:
        filename = f"{uuid.uuid4()}.jpg"
        return filename, {
            "query": query,
            "url": url,
            "caption": caption.strip() or query,
            "datetime": datetime.now().astimezone().isoformat(timespec="seconds"),
            "source": source,
            "public_ip": self.public_ip,
        }

    def _wait_for_more(self, selector: str, previous_count: int, timeout: float = 4) -> bool:
        assert self.wd is not None
        try:
            WebDriverWait(self.wd, timeout).until(
                lambda driver: len(driver.find_elements(By.CSS_SELECTOR, selector)) > previous_count
            )
        except TimeoutException:
            return False
        return True

    def _accept_google_consent(self) -> None:
        assert self.wd is not None
        selectors = (
            "button#L2AGLb",
            "button[jsname='b3VHJd']",
            "form[action*='consent'] button",
        )
        for selector in selectors:
            buttons = self.wd.find_elements(By.CSS_SELECTOR, selector)
            if not buttons:
                continue
            try:
                buttons[0].click()
            except (ElementClickInterceptedException, StaleElementReferenceException):
                logger.debug("Google consent button could not be clicked")
            return

    def _raise_for_access_problem(self, engine: str) -> None:
        """Turn known challenge and error pages into actionable failures."""

        assert self.wd is not None
        current_url = self.wd.current_url.lower()
        try:
            body_text = self.wd.find_element(By.TAG_NAME, "body").text.lower()
        except WebDriverException:
            body_text = ""

        if engine == "google" and ("/sorry/" in current_url or "unusual traffic" in body_text):
            raise SearchEngineAccessError(
                "Google presented an automated-traffic challenge. "
                "Try again later or from a different network."
            )
        if engine == "yahoo" and (
            "http error" in body_text or "currently unable to handle this request" in body_text
        ):
            raise SearchEngineAccessError(
                "Yahoo returned an HTTP error page. Try again later or from a different network."
            )

    def get_google_images(
        self,
        start: int = 0,
        *,
        limit: int | None = None,
    ) -> dict[str, dict[str, str | None]]:
        """Collect Google image thumbnails and their accessible captions."""

        del start  # Retained for backward compatibility with the old method signature.
        assert self.wd is not None
        target_limit = limit or self.cfg.num_images
        image_data: dict[str, dict[str, str | None]] = {}
        seen_urls: set[str] = set()

        for _, query, query_limit in self._query_targets(target_limit):
            self.wd.get(self.set_target_url("google", query))
            self._accept_google_consent()
            self._raise_for_access_problem("google")
            query_start = len(image_data)
            stagnant_rounds = 0

            while len(image_data) - query_start < query_limit and stagnant_rounds < 2:
                elements = self.wd.find_elements(By.CSS_SELECTOR, GOOGLE_IMAGE_SELECTOR)
                before = len(elements)
                for element in elements:
                    try:
                        caption = (
                            element.get_attribute("alt") or element.get_attribute("title") or query
                        )
                        url = self._google_full_image_url(element)
                        if not url or url in seen_urls:
                            continue
                    except StaleElementReferenceException:
                        continue
                    seen_urls.add(url)
                    filename, result = self._result(
                        query=query,
                        url=url,
                        caption=caption,
                        source="google",
                    )
                    image_data[filename] = result
                    if len(image_data) - query_start >= query_limit:
                        break

                if len(image_data) - query_start >= query_limit:
                    break
                self.wd.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                stagnant_rounds = (
                    0 if self._wait_for_more(GOOGLE_IMAGE_SELECTOR, before) else stagnant_rounds + 1
                )

            if len(image_data) == query_start:
                logger.warning("Google returned no usable images for query: {}", query)
        return image_data

    def get_yahoo_images(
        self,
        *,
        limit: int | None = None,
    ) -> dict[str, dict[str, str | None]]:
        """Collect visible Yahoo results before attempting pagination."""

        assert self.wd is not None
        target_limit = limit or self.cfg.num_images
        image_data: dict[str, dict[str, str | None]] = {}
        seen_urls: set[str] = set()

        for _, query, query_limit in self._query_targets(target_limit):
            self.wd.get(self.set_target_url("yahoo", query))
            self._raise_for_access_problem("yahoo")
            query_start = len(image_data)
            stagnant_rounds = 0

            while len(image_data) - query_start < query_limit and stagnant_rounds < 2:
                elements = self.wd.find_elements(By.CSS_SELECTOR, YAHOO_IMAGE_SELECTOR)
                before = len(elements)
                for element in elements:
                    try:
                        caption = (
                            element.get_attribute("alt") or element.get_attribute("title") or query
                        )
                        url = self._yahoo_full_image_url(element)
                        if not url or url in seen_urls:
                            continue
                    except StaleElementReferenceException:
                        continue
                    seen_urls.add(url)
                    filename, result = self._result(
                        query=query,
                        url=url,
                        caption=caption,
                        source="yahoo",
                    )
                    image_data[filename] = result
                    if len(image_data) - query_start >= query_limit:
                        break

                if len(image_data) - query_start >= query_limit:
                    break

                self.wd.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                more_buttons = self.wd.find_elements(By.NAME, "more-res")
                if more_buttons:
                    try:
                        more_buttons[0].click()
                    except (ElementClickInterceptedException, StaleElementReferenceException):
                        logger.debug("Yahoo's more-results button could not be clicked")
                stagnant_rounds = (
                    0 if self._wait_for_more(YAHOO_IMAGE_SELECTOR, before) else stagnant_rounds + 1
                )

            if len(image_data) == query_start:
                logger.warning("Yahoo returned no usable images for query: {}", query)
        return image_data

    def get_flickr_images(
        self,
        *,
        limit: int | None = None,
    ) -> dict[str, dict[str, str | None]]:
        """Collect Flickr image results and captions."""

        assert self.wd is not None
        target_limit = limit or self.cfg.num_images
        image_data: dict[str, dict[str, str | None]] = {}
        seen_urls: set[str] = set()

        for _, query, query_limit in self._query_targets(target_limit):
            self.wd.get(self.set_target_url("flickr", query))
            self._raise_for_access_problem("flickr")
            query_start = len(image_data)
            stagnant_rounds = 0

            while len(image_data) - query_start < query_limit and stagnant_rounds < 2:
                elements = self.wd.find_elements(By.CSS_SELECTOR, FLICKR_ITEM_SELECTOR)
                before = len(elements)
                for element in elements:
                    try:
                        source_url = self._image_source(element)
                        url = self._flickr_large_image_url(source_url) if source_url else None
                        if not url or url in seen_urls:
                            continue
                        caption = (
                            element.get_attribute("aria-label")
                            or element.get_attribute("title")
                            or element.get_attribute("alt")
                            or query
                        )
                    except StaleElementReferenceException:
                        continue
                    seen_urls.add(url)
                    filename, result = self._result(
                        query=query,
                        url=url,
                        caption=caption,
                        source="flickr",
                    )
                    image_data[filename] = result
                    if len(image_data) - query_start >= query_limit:
                        break

                if len(image_data) - query_start >= query_limit:
                    break
                self.wd.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                stagnant_rounds = (
                    0 if self._wait_for_more(FLICKR_ITEM_SELECTOR, before) else stagnant_rounds + 1
                )

            if len(image_data) == query_start:
                logger.warning("Flickr returned no usable images for query: {}", query)
        return image_data

    @staticmethod
    def _query_slug(query: str) -> str:
        slug = re.sub(r"[^a-z0-9._-]+", "_", query.lower()).strip("._")
        return slug or "query"

    @staticmethod
    def _write_json(path: Path, image_data: dict[str, dict[str, str | None]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(".json.tmp")
        with temporary_path.open("w", encoding="utf-8") as output:
            json.dump(image_data, output, ensure_ascii=False, indent=2)
        temporary_path.replace(path)

    def _target_directory(self) -> Path:
        query = self._query_slug(self.cfg.query)
        return self.cfg.out_dir / self.cfg.engine / query

    def save_images_and_captions(
        self,
        image_data: dict[str, dict[str, str | None]],
    ) -> dict[str, dict[str, str | None]]:
        """Download images and save metadata using matching filenames."""

        target_directory = self._target_directory()
        target_directory.mkdir(parents=True, exist_ok=True)
        saved_items: dict[str, dict[str, str | None]] = {}
        headers = {"User-Agent": "image-caption-scraper/0.1"}

        with requests.Session() as session:
            for filename, item in image_data.items():
                try:
                    save_image(
                        str(item["url"]),
                        target_directory / filename,
                        session=session,
                        min_width=self.cfg.min_width,
                        min_height=self.cfg.min_height,
                        request_headers=headers,
                    )
                except (OSError, ValueError, requests.RequestException) as exc:
                    logger.warning("Could not save {}: {}", filename, exc)
                    continue
                saved_items[filename] = item

        metadata_path = target_directory / f"{self._query_slug(self.cfg.query)}.json"
        self._write_json(metadata_path, saved_items)
        logger.info("Saved metadata at: {}", metadata_path.resolve())
        return saved_items

    def save_images_data(
        self,
        image_data: dict[str, dict[str, str | None]],
    ) -> Path:
        """Save metadata without downloading images."""

        target_directory = self._target_directory()
        metadata_path = target_directory / f"{self._query_slug(self.cfg.query)}.json"
        self._write_json(metadata_path, image_data)
        logger.info("Saved metadata at: {}", metadata_path.resolve())
        return metadata_path


# Backward-compatible public name used by versions 0.0.1 through 0.0.3.
Image_Caption_Scraper = ImageCaptionScraper


__all__ = ["ImageCaptionScraper", "Image_Caption_Scraper", "SearchEngineAccessError"]
