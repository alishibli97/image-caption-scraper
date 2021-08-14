# image-caption-scraper

## About
This package allows downloading images and their corresponding captions from web search engines like Google Images, Yahoo Image, Flickr, and more to come.

## Installation
`pip install -i https://test.pypi.org/simple/ image-caption-scraper-test`

## Requirements
Python 3.6 or later with all [requirements.txt](https://github.com/alishibli97/image-caption-scraper/blob/main/requirements.txt) dependencies installed. To install run:

`pip install -r requirements.txt`

## Usage
```
from image_caption_scraper import Image_Caption_Scraper

scraper = Image_Caption_Scraper(
                engine="all", # or "google", "yahoo", "flickr"
                num_images=100,
                query="dog chases cat",
                out_dir="images",
                headless=True,
                driver="chromedriver",
                expand=True,
                k=3
            )

scraper.scrape(save_images=True)
```
###### Options
| Argument        | Description           | Options  |
| ------------- |:-------------:| -----:|
| engine      | the search engine to scrape images from. By default it searches through all the available engines (now Google, Flickr, Yahoo). | "all","google","flickr","yahoo" |
| num_images      | centered      |   $12 |
| query | are neat      |    $1 |
| out_dir | are neat      |    $1 |
| headless | are neat      |    $1 |
| expand | are neat      |    $1 |

1. engine: the search engine to scrape images from. By default it searches through all the available engines (now Google, Yahoo, Flickr).
