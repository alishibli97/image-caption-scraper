# image-caption-scraper

[![CI](https://github.com/alishibli97/image-caption-scraper/actions/workflows/ci.yml/badge.svg)](https://github.com/alishibli97/image-caption-scraper/actions/workflows/ci.yml)
[![Downloads](https://static.pepy.tech/badge/image-caption-scraper)](https://pepy.tech/project/image-caption-scraper)

![image-caption-scraper logo](new_logo.jpg)

Download image-search results together with captions and JSON metadata. The
package currently supports Google Images, Yahoo Images, and Flickr through
Selenium.

> Search-engine page structure changes regularly. Treat individual engines as
> experimental and please report a reproducible issue when an engine changes.

## Installation

image-caption-scraper requires Python 3.10 or later and a Chrome/Chromium
installation.

```bash
python -m pip install image-caption-scraper
```

Recent Selenium versions use Selenium Manager to locate or download a matching
driver automatically. An explicit ChromeDriver path can still be provided when
automatic management is unavailable.

Optional query features are installed separately:

```bash
# WordNet query expansion
python -m pip install 'image-caption-scraper[expand]'

# T5-based translation (downloads a model on first use)
python -m pip install 'image-caption-scraper[translate]'
```

WordNet expansion also needs the corresponding NLTK data once:

```python
import nltk

nltk.download("averaged_perceptron_tagger_eng")
nltk.download("punkt_tab")
nltk.download("wordnet")
```

## Usage

```python
from image_caption_scraper import ImageCaptionScraper

scraper = ImageCaptionScraper(
    engine="all",  # google, yahoo, flickr, or all
    num_images=100,
    query="dog chases cat",
    out_dir="images",
    headless=True,
)

results = scraper.scrape(save_images=True)
```

`scrape()` returns the collected metadata and closes Chrome by default. To keep
the browser available for another operation, pass `close_driver=False` and call
`scraper.close()` afterward. The previous `Image_Caption_Scraper` class name is
still available as a compatibility alias.

To save URLs and metadata without downloading the images:

```python
results = scraper.scrape(save_images=False)
```

Results are written under:

```text
<out_dir>/<engine>/<query>/<query>.json
```

Each JSON entry contains the query, image URL, caption, timestamp, source, and
optional public IP. Public-IP collection is disabled by default; enable it only
when it is genuinely needed with `collect_public_ip=True`.

## Options

| Argument | Description | Default |
| --- | --- | --- |
| `engine` | `google`, `yahoo`, `flickr`, or `all` | `all` |
| `num_images` | Maximum number of results | `100` |
| `query` | Image-search query | `dog chases cat` |
| `out_dir` | Output directory | `images` |
| `headless` | Run Chrome without a visible window | `True` |
| `driver` | Optional path to ChromeDriver | Selenium Manager |
| `expand` | Generate WordNet query variations | `False` |
| `translate` | Add French, German, and Romanian T5 translations | `False` |
| `k` | Synonyms retained per query word during expansion | `3` |
| `collect_public_ip` | Include the machine's public IP in metadata | `False` |

## Development

```bash
git clone https://github.com/alishibli97/image-caption-scraper.git
cd image-caption-scraper
python -m pip install -e '.[test]'
pytest
```

The automated tests do not contact search engines. Live scraping should be
tested with a small result count because websites can present regional consent
pages, rate limits, or CAPTCHA challenges. Known automated-traffic challenges
and HTTP error pages raise `SearchEngineAccessError` instead of silently
returning no results.

## Responsible use

Review each site's terms and robots guidance, respect rate limits, and verify
that you have the necessary rights to download and use the images and captions.
This package does not grant rights to third-party content.

## License

Distributed under the MIT License. See [LICENSE](LICENSE).
