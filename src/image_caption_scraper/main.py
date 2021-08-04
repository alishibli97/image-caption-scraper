import argparse
from .expansion import *
from .scraper import *

def run():

    with open('data.json', 'r') as fp:
        args = json.load(fp)

    # parser = argparse.ArgumentParser()
    # parser.add_argument('--num_images',required=True,type=int)
    # parser.add_argument('--query',required=True,type=str)
    # parser.add_argument('--engine',type=str)
    # parser.add_argument('--out_dir',type=str,default='images')
    # parser.add_argument('--headless', action='store_true')
    # parser.add_argument('--driver', type=str,default="chromedriver")
    # parser.add_argument('--expand', action='store_true')
    # parser.add_argument('--k', type=int, default=3)
    # args = parser.parse_args()

    if args.expand:
        synonyms = generate_synonyms(args.query,args.k)
        # queries_expanded = list(set([trans for synonym in synonyms for trans in translate(synonym)]))
        
        queries_expanded = synonyms

        print(queries_expanded)

        img_data = {}
        # print(queries_expanded)
        args.num_images /= len(queries_expanded)
        for i,query in enumerate(queries_expanded):
            logger.info(f"Scraping for query {i}")
            args.query = query

            cfg = parse_args(args)

            scraper = Image_Caption_Scraper(cfg)

            new = scraper.scrape()
            print(len(new))

            img_data = {**img_data, **new}

            logger.info(f"The new length is {len(img_data)}")
            print()

            # scraper.save_images_and_captions(img_data)

        scraper.save_images_data(img_data)