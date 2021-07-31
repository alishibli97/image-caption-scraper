from nltk.corpus import wordnet
from nltk import word_tokenize, pos_tag
import itertools

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

def translate():
    pass

# phrase = "I love to play football"
# k = 10
# synonyms = generate_synonyms(phrase,k)

