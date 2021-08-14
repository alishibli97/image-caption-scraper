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
### Options
| Argument        | Description           | Options  |
| ------------- |:-------------:| -----:|
| engine      | Search engine to scrape images from. By default it searches through all the available engines (currently supports Google, Flickr, Yahoo). | "all","google","flickr","yahoo" |
| num_images      | Number of images targetted by the user      |  Any number (int) > 0 |
| query | The text query to search for      | Any text query |
| out_dir | Output directly to save the images and captions      |  Any text string |
| headless | Argument to hide the browser while crawling the web pages or show it. True will hide, False will open it  | 'True' or 'False' |
| expand | Argument to expand the input query. Expansions supports synonyms from wordnet at the moment. Translations are coming soon.   | 'True' or 'False' |
| driver | The web driver to navigate the web pages. Download the driver from https://chromedriver.chromium.org/ | Default='chromedriver' (configured in System Path). Otherwise just type the path to the .exe file |
| k | If expand==True, k determines how many synonyms to fetch from wordnet for each word in the query. It is assumed that words are separated by spaces. The model fetches the closest k synonyms for each word by path_similarity in the wordnet graph.   | 'True' or 'False' |
| save_images | If True the model will save the images+captions in the out_dir folder. Otherwise it will only save the meta-data (with urls) without the images. | 'True' or 'False' |

## License

Distributed under the MIT License. See `LICENSE` for more information.

## TODO
1. Verify large dataset collections (quality and time wise)
2. Implement parallel execution for faster data collection
3. Expand queries using more methods like transations and other.

## Contact
Email: alishibli97@hotmail.com
