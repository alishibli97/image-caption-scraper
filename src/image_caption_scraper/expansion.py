from nltk.corpus import wordnet
from nltk import word_tokenize, pos_tag
import itertools
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
from loguru import logger

def get_wordnet_pos(treebank_tag):

    if treebank_tag.startswith('J'):
        return wordnet.ADJ
    elif treebank_tag.startswith('V'):
        return wordnet.VERB
    elif treebank_tag.startswith('N'):
        return wordnet.NOUN
    elif treebank_tag.startswith('R'):
        return wordnet.ADV
    else:
        return ''

def generate_synonyms(phrase,k):

    words_pos = pos_tag(word_tokenize(phrase))
    
    synonyms = []
    for (word,pos) in words_pos:
        temp = {}
        wn_pos = get_wordnet_pos(pos)
        if wn_pos:
            for syn in wordnet.synsets(word,pos=wn_pos):
                original = wordnet.synsets(word,pos=wn_pos)[0]
                path_similarity = original.path_similarity(syn)
                for l in syn.lemmas():
                    if ((l.name() not in temp) or ((l.name() in temp) and (temp[l.name()]<path_similarity))):
                        temp[l.name()] = original.path_similarity(syn)
        else:
            temp[word] = 1.0

        temp = list(dict(sorted(temp.items(), key=lambda item: item[1],reverse=True)).keys())[:k]
        synonyms.append(temp)

    results = []
    for element in itertools.product(*synonyms):
        results.append(" ".join(element))
    
    return results

def translate(phrase,driver="chromedriver"):
    chrome_options = Options()
    chrome_options.headless = True
    wd = webdriver.Chrome(options=chrome_options,executable_path=driver)

    # cookie accept
    tl = "ar"
    wd.get("https://translate.google.com.lb/?hl=en&tab=wT&sl=en&tl={tl}&text={phrase}&op=translate")
    button = wd.find_element_by_xpath("/html/body/c-wiz/div/div/div/div[2]/div[1]/div[4]/form/div[1]/div/button/span")
    button.click()

    # target_languages = open("codes.txt").read().split()
    target_languages = [
        'zh', # chinese
        # 'hi', # hindu
        'es', # spanish
        'ar', # arabic
        # 'ms', # malay
        'ru', # russian
        # 'bn', # bengali
        # 'pt', # portugese
        'fr', # french

        'sv', # swedish
        # 'it', # italian
        # 'ga', # irish
    ]

    results = []
    for i,tl in enumerate(target_languages):
        # logger.info(f"Finished transation {i}/{len(target_languages)}")
        print(f"Finished transation {i}/{len(target_languages)}",end="\r")
        link = f"https://translate.google.com.lb/?hl=en&tab=wT&sl=en&tl={tl}&text={phrase}&op=translate"
        wd.get(link)
        time.sleep(2)
        result = wd.find_element_by_xpath("/html/body/c-wiz/div/div[2]/c-wiz/div[2]/c-wiz/div[1]/div[2]/div[2]/c-wiz[2]/div[5]/div/div[1]/span[1]/span/span").text
        results.append(result)
    
    return results

# phrase = "I love to play football"
# k = 5
# synonyms = generate_synonyms(phrase,k)

# print(synonyms)

# translate("ali please can you play with me?")