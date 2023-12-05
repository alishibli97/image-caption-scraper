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

def translate_query(tokenizer, model, query, languages=["French", "German", "Romanian"]):
    translations = {"English": query}
    for language in languages:
        task_prefix = f"translate English to {language}: "
        inputs = tokenizer(task_prefix + query, 
                                return_tensors="pt", padding=True)

        output_sequences = model.generate(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            do_sample=False  # Disable sampling
        )

        translations[language] = tokenizer.batch_decode(output_sequences, skip_special_tokens=True)[0]
    return translations

# phrase = "I love to play football"
# k = 5
# synonyms = generate_synonyms(phrase,k)

# print(synonyms)

# translate("ali please can you play with me?")