# image-caption-scraper

![alt text](https://github.com/alishibli97/image-caption-scraper/blob/main/new_logo.jpg)


## About

This package allows downloading images and their corresponding captions from web search engines like Google Images, Yahoo Image, Flickr, and more to come.

The model is particularly targetting researchers for building their own datasets of their own concepts, and can thus train machine learning models for computer vision, natural language processing, and the intersection of both (image captioning, visual relationship detection).

The pipeline is completely based on Selenium web driver.



<!--
### Table of Contents
**[Installation](#Installation)**<br>
**[Requirements](#Requirements)**<br>
**[Usage](#Usage)**<br>
**[Contact](#Contact)**<br>
**[TODO](#TODO)**<br> 
-->

<details open="open">
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#Installation">Installation</a></li>
    <li><a href="#Requirements">Requirements</a></li>
    <li>
      <a href="#Usage">Usage</a>
      <ul>
        <li><a href="#Options">Options</a></li>
      </ul>
    </li>
    <li><a href="#License">License</a></li>
    <li><a href="#Contact">Contact</a></li>
    <li><a href="#TODO">TODO</a></li>
  </ol>
</details>

## Installation
`pip install image-caption-scraper`

## Requirements
Python 3.6 or later with all [requirements.txt](https://github.com/alishibli97/image-caption-scraper/blob/main/requirements.txt) dependencies installed. To install run:

`pip install -r requirements.txt`

Also, make sure to download chrome-driver from https://chromedriver.chromium.org/ and either add it to the system variables path, or type down the full path to the .exe file in the options below.

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
                expand=False,
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

## Contact
Email: alishibli97@hotmail.com

## TODO
1. Verify large dataset collections (quality and time wise)
2. Implement parallel execution for faster data collection
3. Expand queries using more methods like transations and other.
