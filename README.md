# image-caption-scraper

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
