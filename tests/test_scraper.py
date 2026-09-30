import base64
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from PIL import Image

from image_caption_scraper import (
    Image_Caption_Scraper,
    ImageCaptionScraper,
    SearchEngineAccessError,
)
from image_caption_scraper.helper import ScraperConfig, save_image

ONE_PIXEL_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def scraper_without_browser(config: ScraperConfig) -> ImageCaptionScraper:
    scraper = ImageCaptionScraper.__new__(ImageCaptionScraper)
    scraper.cfg = config
    scraper.public_ip = None
    scraper.wd = None
    return scraper


class FakeElement:
    def __init__(self, text="", **attributes):
        self.attributes = attributes
        self.text = text

    def get_attribute(self, name):
        return self.attributes.get(name)


class FakeDriver:
    def __init__(self, result_selector, element, *, full_image=None, yahoo_metadata=None):
        self.result_selector = result_selector
        self.element = element
        self.full_image = full_image
        self.yahoo_metadata = yahoo_metadata or []
        self.visited_url = None

    def get(self, url):
        self.visited_url = url

    @property
    def current_url(self):
        return self.visited_url or ""

    def find_elements(self, _by, selector):
        if selector == "img.sFlh5c.iPVvYb, img.n3VNCb" and self.full_image:
            return [self.full_image]
        return [self.element] if selector == self.result_selector else []

    def find_element(self, _by, _selector):
        return FakeElement(text="")

    def execute_script(self, script, *args):
        if "naturalWidth" in script:
            element = args[0]
            return [
                element.get_attribute("natural_width") or 0,
                element.get_attribute("natural_height") or 0,
            ]
        if "flatMap" in script:
            return self.yahoo_metadata
        return None


def test_old_class_name_is_preserved():
    assert Image_Caption_Scraper is ImageCaptionScraper


@pytest.mark.parametrize("engine", ["all", "google", "yahoo", "flickr"])
def test_config_accepts_supported_engines(engine):
    assert ScraperConfig(engine=engine).engine == engine


@pytest.mark.parametrize(
    ("kwargs", "exception"),
    [
        ({"engine": "unknown"}, ValueError),
        ({"num_images": 0}, ValueError),
        ({"num_images": 1.5}, TypeError),
        ({"query": "  "}, ValueError),
        ({"k": 0}, ValueError),
        ({"min_width": 0}, ValueError),
        ({"min_height": 0}, ValueError),
    ],
)
def test_config_rejects_invalid_values(kwargs, exception):
    with pytest.raises(exception):
        ScraperConfig(**kwargs)


def test_search_url_encodes_query():
    scraper = scraper_without_browser(ScraperConfig(query="cats & dogs"))

    url = scraper.set_target_url("google", scraper.cfg.query)

    assert parse_qs(urlparse(url).query) == {"tbm": ["isch"], "q": ["cats & dogs"]}


@pytest.mark.parametrize(
    ("engine", "selector", "attributes", "expected_url"),
    [
        (
            "google",
            "img.YQ4gaf, img.Q4LuWd",
            {"src": "data:image/gif;base64,AA==", "data-src": "https://example.com/g.jpg"},
            "https://example.com/google-full.jpg",
        ),
        (
            "yahoo",
            "#sres li img, ul#sres img",
            {"src": "https://example.com/y.jpg"},
            "https://example.com/y.jpg",
        ),
        (
            "flickr",
            ".photo-list-photo-view img",
            {"src": "//live.staticflickr.com/1234/photo_m.jpg"},
            "https://live.staticflickr.com/1234/photo_b.jpg",
        ),
    ],
)
def test_each_engine_collects_a_result(engine, selector, attributes, expected_url):
    scraper = scraper_without_browser(ScraperConfig(engine=engine, num_images=1, query="cat"))
    full_image = None
    yahoo_metadata = None
    if engine == "google":
        full_image = FakeElement(
            src=expected_url,
            natural_width=1200,
            natural_height=800,
        )
    elif engine == "yahoo":
        yahoo_metadata = [json.dumps({"iurl": expected_url})]
    scraper.wd = FakeDriver(
        selector,
        FakeElement(alt="caption", **attributes),
        full_image=full_image,
        yahoo_metadata=yahoo_metadata,
    )

    results = getattr(scraper, f"get_{engine}_images")(limit=1)
    result = next(iter(results.values()))

    assert result["url"] == expected_url
    assert result["source"] == engine
    assert "cat" in scraper.wd.visited_url


@pytest.mark.parametrize(
    "url",
    [
        "https://combo.staticflickr.com/pw/favicon.ico",
        "https://media.istockphoto.com/id/example/photo.jpg",
        "https://www.flickr.com/images/logo.png",
    ],
)
def test_flickr_rejects_site_assets_and_ads(url):
    assert ImageCaptionScraper._flickr_large_image_url(url) is None


def test_yahoo_extracts_original_url_from_result_link():
    value = "https://images.search.yahoo.com/view?imgurl=https%3A%2F%2Fexample.com%2Foriginal.jpg"

    assert ImageCaptionScraper._url_from_yahoo_metadata([value]) == (
        "https://example.com/original.jpg"
    )


@pytest.mark.parametrize(
    ("engine", "current_url", "body"),
    [
        ("google", "https://www.google.com/sorry/index", "Unusual traffic"),
        ("yahoo", "https://images.search.yahoo.com", "HTTP ERROR 500"),
    ],
)
def test_engine_error_pages_raise_actionable_error(engine, current_url, body):
    scraper = scraper_without_browser(ScraperConfig(engine=engine, num_images=1))
    driver = FakeDriver("unused", FakeElement())
    driver.visited_url = current_url
    driver.find_element = lambda *_: FakeElement(text=body)
    scraper.wd = driver

    with pytest.raises(SearchEngineAccessError):
        scraper._raise_for_access_problem(engine)


def test_metadata_save_does_not_change_working_directory(tmp_path, monkeypatch):
    working_directory = tmp_path / "working"
    working_directory.mkdir()
    monkeypatch.chdir(working_directory)
    output = tmp_path / "output"
    scraper = scraper_without_browser(
        ScraperConfig(engine="google", query="../../Unsafe query", out_dir=output)
    )
    data = {
        "one.jpg": {
            "query": "../../Unsafe query",
            "url": "https://example.com/one.jpg",
            "caption": "example",
            "datetime": "2026-01-01T00:00:00+00:00",
            "source": "google",
            "public_ip": None,
        }
    }

    metadata_path = scraper.save_images_data(data)

    assert Path.cwd() == working_directory
    assert metadata_path.is_relative_to(output)
    assert json.loads(metadata_path.read_text(encoding="utf-8")) == data


def test_base64_image_is_saved_as_jpeg(tmp_path):
    # A 1x1 transparent PNG.
    png = base64.b64decode(ONE_PIXEL_PNG)
    destination = tmp_path / "image.jpg"

    save_image(
        f"data:image/png;base64,{base64.b64encode(png).decode()}",
        destination,
    )

    with Image.open(destination) as image:
        assert image.format == "JPEG"
        assert image.mode == "RGB"


def test_downloaded_filename_matches_metadata_key(tmp_path):
    scraper = scraper_without_browser(
        ScraperConfig(
            engine="google",
            query="example",
            out_dir=tmp_path,
            min_width=1,
            min_height=1,
        )
    )
    data = {
        "matching-name.jpg": {
            "query": "example",
            "url": f"data:image/png;base64,{ONE_PIXEL_PNG}",
            "caption": "example caption",
            "datetime": "2026-01-01T00:00:00+00:00",
            "source": "google",
            "public_ip": None,
        }
    }

    saved = scraper.save_images_and_captions(data)
    target = tmp_path / "google" / "example"
    metadata = json.loads((target / "example.json").read_text(encoding="utf-8"))

    assert (target / "matching-name.jpg").is_file()
    assert saved == data
    assert metadata == data


def test_scraper_rejects_tiny_downloads(tmp_path):
    scraper = scraper_without_browser(
        ScraperConfig(engine="google", query="example", out_dir=tmp_path)
    )
    data = {
        "tiny.jpg": {
            "query": "example",
            "url": f"data:image/png;base64,{ONE_PIXEL_PNG}",
            "caption": "tiny",
            "datetime": "2026-01-01T00:00:00+00:00",
            "source": "google",
            "public_ip": None,
        }
    }

    saved = scraper.save_images_and_captions(data)

    assert saved == {}
    assert not (tmp_path / "google" / "example" / "tiny.jpg").exists()


def test_scrape_closes_driver_by_default(tmp_path):
    class FakeDriver:
        closed = False

        def quit(self):
            self.closed = True

    scraper = scraper_without_browser(ScraperConfig(out_dir=tmp_path))
    driver = FakeDriver()
    scraper.wd = driver
    scraper.crawl = dict

    result = scraper.scrape(save_images=False)

    assert result == {}
    assert driver.closed is True
    assert scraper.wd is None


def test_query_targets_share_the_requested_limit():
    config = ScraperConfig(num_images=5)
    config.queries.update({"French": "chats", "German": "katzen"})
    scraper = scraper_without_browser(config)

    targets = scraper._query_targets(5)

    assert [target for _, _, target in targets] == [2, 2, 1]
    assert sum(target for _, _, target in targets) == 5
