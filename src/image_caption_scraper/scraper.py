import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from loguru import logger
from datetime import datetime
import re
import json
import os
from pathlib import Path
from .helper import *
import uuid
import json
from .expansion import *
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException

# print(uuid.uuid4())

class Image_Caption_Scraper():

    def __init__(self,engine="all",num_images=100,query="dog chases cat",out_dir="images",headless=True,driver="chromedriver",expand=False,k=3):
        """Initialization is only starting the web driver and getting the public IP address"""
        logger.info("Initializing scraper")
        
        self.public_ip = self.get_public_ip_address()
        self.google_start_index = 0

        self.cfg = parse_args(engine,num_images,query,out_dir,headless,driver,expand,k)
        self.start_web_driver()

    def get_public_ip_address(self):
        """Read the public IP address of the host"""
        response = requests.get('https://api.ipify.org')
        return response.text

    def start_web_driver(self):
        """Create the webdriver and point it to the specific search engine"""
        logger.info("Starting the engine")
        chrome_options = Options()

        if self.cfg.headless:
            chrome_options.add_argument("--headless")

        self.wd = webdriver.Chrome(options=chrome_options) # service=Service(executable_path=self.cfg.driver)


    def scrape(self,save_images=True):
        """Main function to scrape"""
        img_data = {}
        if self.cfg.expand:
            queries_expanded = generate_synonyms(self.cfg.query,self.cfg.k)
            # queries_expanded = list(set([trans for synonym in synonyms for trans in translate(synonym)]))

            self.cfg.num_images /= len(queries_expanded)
            for i,query in enumerate(queries_expanded):
                logger.info(f"Scraping for query {query} ({i}/{len(queries_expanded)} queries)")
                self.cfg.query = query
                new_data = self.crawl()
                img_data = {**img_data, **new_data}
        else:
            logger.info(f"Scraping for query {self.cfg.query}")
            img_data = self.crawl()

        if save_images:
            self.save_images_and_captions(img_data)
        else:
            self.save_images_data(img_data)

    def crawl(self):
        if self.cfg.engine=='google': img_data = self.get_google_images()
        elif self.cfg.engine=='yahoo': img_data = self.get_yahoo_images()
        elif self.cfg.engine=='flickr': img_data = self.get_flickr_images()
        else: # all 3
            self.cfg.num_images = int(self.cfg.num_images/3) + 1
            img_data1 = self.get_google_images()
            img_data2 = self.get_yahoo_images()
            if not img_data2:
                self.google_start_index += self.cfg.num_images
                img_data2 = self.get_google_images(self.google_start_index)
            img_data3 = self.get_flickr_images()
            if len(img_data3)<self.cfg.num_images:
                self.google_start_index += self.cfg.num_images
                img_data3 = self.get_google_images(self.google_start_index)
            img_data = {**img_data1,**img_data2,**img_data3}
        return img_data

    def set_target_url(self,engine):
        """Given the target engine and query, build the target url"""
        url_index = {
            'google': "https://www.google.com/search?safe=off&site=&tbm=isch&source=hp&q={}&oq={}&gs_l=img".format(self.cfg.query,self.cfg.query),
            'yahoo': "https://images.search.yahoo.com/search/images;?&p={}&ei=UTF-8&iscqry=&fr=sfp".format(self.cfg.query),
            'flickr': "https://www.flickr.com/search/?text={}".format(self.cfg.query)
        }
        if not engine in url_index: 
            logger.error(f"Please choose {' or '.join(k for k in url_index)}.")
            return
        self.target_url = url_index[engine]

    def scroll_to_end(self):
        """Function for Google Images to scroll to new images after finishing all existing images"""
        logger.info("Loading new images")
        self.wd.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)

    def load_yahoo(self):
        """Function for Yahoo Images to scroll to new images after finishing all existing images"""
        logger.info("Loading new images")
        button = self.wd.find_element(By.NAME, 'more-res')
        button.click()
        time.sleep(3)

    def get_google_images(self,start=0):
        """Retrieve urls for images and captions from Google Images search engine"""
        logger.info("Scraping google images")
        self.set_target_url("google")

        self.wd.get(self.target_url)

        time.sleep(2)
        try:
            button = self.wd.find_element(By.XPATH, "//button[contains(@class, 'VfPpkd-LgbsSe') and @jsname='b3VHJd']")
            button.click()
            time.sleep(2)
        except (NoSuchElementException, ElementClickInterceptedException):
            # Handle the exception or just pass
            pass

        img_data = {}

        # start = 0
        prevLength = 0
        while(len(img_data)<self.cfg.num_images):
            self.scroll_to_end();i=0

            thumbnail_results = self.wd.find_elements(By.CSS_SELECTOR, "img.Q4LuWd")

            if(len(thumbnail_results)==prevLength):
                logger.info("Loaded all images for Google")
                break

            prevLength = len(thumbnail_results)
            # logger.info(f"There are {len(thumbnail_results)} images")

            for i,content in enumerate(thumbnail_results[start:len(thumbnail_results)]):
                try:
                    self.wd.execute_script("arguments[0].click();", content)
                    time.sleep(1)

                    common_path = f'//*[@id="islrg"]/div[1]/div[{i+1}]'

                    caption = self.wd.find_element(By.XPATH, f'{common_path}/a[2]').text

                    # url = self.wd.find_elements_by_css_selector('img.n3VNCb')[0]
                    
                    url = self.wd.find_element(By.XPATH, f'{common_path}/a[1]/div[1]/img')

                    if url.get_attribute('src') and not url.get_attribute('src').endswith('gif') and url.get_attribute('src') not in img_data:

                        now = datetime.now().astimezone()
                        now = now.strftime("%m-%d-%Y %H:%M:%S %z %Z")

                        name = uuid.uuid4() # len(img_data)
                        img_data[f'{name}.jpg']={
                            'query':self.cfg.query,
                            'url':url.get_attribute('src'),
                            'caption':caption,
                            'datetime': now,
                            'source': 'google',
                            'public_ip': self.public_ip
                        }
                        logger.info(f"Finished {len(img_data)}/{self.cfg.num_images} images for Google.")
                except:
                    logger.debug("Couldn't load image and caption for Google")
                
                if(len(img_data)>self.cfg.num_images-1): 
                    logger.info(f"Finished scraping {self.cfg.num_images} for Google!")
                    # logger.info("Loaded all the images and captions!")
                    break
            
            start = len(thumbnail_results)

        return img_data

    def get_yahoo_images(self):
        """Retrieve urls for images and captions from Yahoo Images search engine"""
        logger.info("Scraping yahoo images")
        self.set_target_url("yahoo")

        self.wd.get(self.target_url)

        img_data = {}

        start = 0
        i=0
        while(len(img_data)<self.cfg.num_images):
            # Accept cookie
            try:
                button = self.wd.find_element(By.XPATH, '//*[@id="consent-page"]/div/div/div/form/div[2]/div[2]/button')
                button.click()
            except:
                pass

            # self.scroll_to_end()
            try: self.load_yahoo()
            except: 
                logger.info("Loaded all images for Yahoo")
                break

            html_list = self.wd.find_element(By.XPATH, '//*[@id="sres"]')
            items = html_list.find_elements(By.TAG_NAME, "li")

            # logger.info(f"There are {len(items)} images")

            for content in items[start:len(items)-1]:
                try:
                    self.wd.execute_script("arguments[0].click();", content)
                    time.sleep(0.5)
                except: # Exception as e:
                    new_html_list = self.wd.find_element(By.ID,"sres")
                    new_items = new_html_list.find_elements(By.TAG_NAME,"li")
                    item = new_items[i]
                    self.wd.execute_script("arguments[0].click();", item)
                i+=1
                # caption = self.wd.find_element_by_class_name('title').text

                try:
                    url = content.find_element(By.TAG_NAME,'img')

                    if url.get_attribute('src') and not url.get_attribute('src').endswith('gif') and url.get_attribute('src') not in img_data:

                        now = datetime.now().astimezone()
                        now = now.strftime("%m-%d-%Y %H:%M:%S %z %Z")

                        name = uuid.uuid4() # len(img_data)
                        img_data[f'{name}.jpg']={
                            'query':self.cfg.query,
                            'url':url.get_attribute('src'),
                            'caption':self.cfg.query, # caption
                            'datetime': now,
                            'source': 'google',
                            'public_ip': self.public_ip
                        }
                        logger.info(f"Finished {len(img_data)}/{self.cfg.num_images} images for Yahoo.")
                
                except:
                    logger.debug("Couldn't load image and caption for Yahoo")

                if(len(img_data)>self.cfg.num_images-1): 
                    logger.info(f"Finished scraping {self.cfg.num_images} for Yahoo!")
                    break
            
            start = len(items)
        return img_data

    def get_flickr_images(self):
        """Retrieve urls for images and captions from Flickr Images search engine"""
        logger.info("Scraping flickr images")
        self.set_target_url("flickr")

        self.wd.get(self.target_url)
        img_data = {}

        start = 0
        prevLength = 0
        waited = False
        while(len(img_data)<self.cfg.num_images):
            self.scroll_to_end()
            # scroll_to_end_flickr()

            items = self.wd.find_elements(By.XPATH, '/html/body/div[1]/div/main/div[2]/div/div[2]/div')

            if(len(items)==prevLength):
                if not waited:
                    self.wd.implicitly_wait(25)
                    waited = True
                else:
                    # print("Loaded all images")
                    break
            prevLength = len(items)

            for item in items[start:len(items)-1]:
                style = item.get_attribute('style')
                url = re.search(r'url\("//(.+?)"\);',style)
                if url: 
                    try:
                        url = "http://"+url.group(1)
                        caption = item.find_element(By.CLASS_NAME, 'interaction-bar').get_attribute('title')
                        caption = caption[:re.search(r'\bby\b',caption).start()].strip()
                        # img_data[url]=caption

                        now = datetime.now().astimezone()
                        now = now.strftime("%m-%d-%Y %H:%M:%S %z %Z")

                        name = uuid.uuid4() # len(img_data)
                        img_data[f'{name}.jpg']={
                            'query':self.cfg.query,
                            'url':url,
                            'caption':caption,
                            'datetime': now,
                            'source': 'flickr',
                            'public_ip': self.public_ip
                        }

                        logger.info(f"Finished {len(img_data)}/{self.cfg.num_images} images for Flickr.")
                    except: pass                    
                if(len(img_data)>self.cfg.num_images-1): 
                    logger.info(f"Finished scraping {self.cfg.num_images} for Flickr!")
                    break
            start = len(items)
        return img_data

    def save_images_and_captions(self,img_data):
        """Retrieve the images and save them in directory with the captions"""
        query = '_'.join(self.cfg.query.lower().split())
        
        out_dir = self.cfg.out_dir
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        os.chdir(out_dir)

        target_folder = os.path.join(f'{self.cfg.engine}', query)
        Path(target_folder).mkdir(parents=True, exist_ok=True)

        result_items = img_data.copy()

        for i,(key,val) in enumerate(img_data.items()):
            try:
                url = val['url']

                if(url.startswith('http')):
                    read_http(url,self.cfg.engine,query,i)

                elif(url.startswith('data')):
                    read_base64(url,self.cfg.engine,query,i)

                else:
                    del result_items[key]
                    logger.debug(f"Couldn't save image {i}: not http nor base64 encoded.")
            except:
                del result_items[key]
                logger.debug(f"Couldn't save image {i}")

        file_path = f'{self.cfg.engine}/{query}/{query}.json'
        with open(file_path, 'w+') as fp:
            json.dump(result_items, fp)
        logger.info(f"Saved urls file at: {os.path.join(os.getcwd(),file_path)}")

    def save_images_data(self,img_data):
        """Save only the meta data without the images"""
        query = '_'.join(self.cfg.query.lower().split())
        out_dir = self.cfg.out_dir
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        os.chdir(out_dir)

        file_path = f'{self.cfg.engine}/{query}'
        Path(file_path).mkdir(parents=True, exist_ok=True)
        file_path += f'/{query}.json'
        with open(file_path, 'w+') as fp:
            json.dump(img_data, fp)
        logger.info(f"Saved json data file at: {os.path.join(os.getcwd(),file_path)}")
