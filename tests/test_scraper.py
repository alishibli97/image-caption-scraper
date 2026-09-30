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
    def __init__(self, result_selector, element):
        self.result_selector = result_selector
        self.element = element
        self.visited_url = None

    def get(self, url):
        self.visited_url = url

    @property
    def current_url(self):
        return self.visited_url or ""

    def find_elements(self, _by, selector):
        return [self.element] if selector == self.result_selector else []

    def find_element(self, _by, _selector):
        return FakeElement(text="")


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
            "https://example.com/g.jpg",
        ),
        (
            "yahoo",
            "#sres li img, ul#sres img",
            {"src": "https://example.com/y.jpg"},
            "https://example.com/y.jpg",
        ),
        (
            "flickr",
            ".photo-list-photo-view, [style*='background-image'], main img",
            {"style": 'background-image: url("//example.com/f.jpg")'},
            "https://example.com/f.jpg",
        ),
    ],
)
def test_each_engine_collects_a_result(engine, selector, attributes, expected_url):
    scraper = scraper_without_browser(ScraperConfig(engine=engine, num_images=1, query="cat"))
    scraper.wd = FakeDriver(selector, FakeElement(alt="caption", **attributes))

    results = getattr(scraper, f"get_{engine}_images")(limit=1)
    result = next(iter(results.values()))

    assert result["url"] == expected_url
    assert result["source"] == engine
    assert "cat" in scraper.wd.visited_url


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
        ScraperConfig(engine="google", query="example", out_dir=tmp_path)
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
