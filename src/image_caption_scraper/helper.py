import requests
import io
from PIL import Image
import os
from loguru import logger
import base64


def read_http(url, engine, query, i):
    # logger.info("Image is http")
    img_content = requests.get(url).content
    img_file = io.BytesIO(img_content)
    img = Image.open(img_file)
    try:
        img = img.convert('RGB')
    except:
        pass
    file_path = os.path.join(f'{engine}/{query}/{i}.jpg')
    with open(file_path, 'wb') as f:
        img.save(f, "JPEG", quality=95)
        logger.info(f"Saved image {i}")

def read_base64(url, engine, query, i):
    # logger.info("Image is base64")
    base64_img = url.split(',')[1]
    img = Image.open(io.BytesIO(base64.b64decode(base64_img)))
    img = img.convert("RGB")
    file_path = os.path.join(f'{engine}/{query}/{i}.jpg')
    with open(file_path, "wb") as f:
        img.save(f, "JPEG", quality=95)
    logger.info(f"Saved image {i}")

class parse_args():
    def __init__(self,engine,num_images,query,out_dir,headless,driver,expand,k):
        self.engine = engine
        self.num_images = num_images
        self.query = query
        self.out_dir = out_dir
        self.headless = headless
        self.driver = driver
        self.expand = expand
        self.k = k