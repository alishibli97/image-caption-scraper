"""Optional query expansion and translation features."""

from __future__ import annotations

import itertools
from typing import Any


def _load_nltk() -> tuple[Any, Any, Any]:
    try:
        from nltk import pos_tag, word_tokenize
        from nltk.corpus import wordnet
    except ImportError as exc:
        raise RuntimeError(
            "Query expansion requires the optional dependencies. "
            "Install them with: pip install 'image-caption-scraper[expand]'"
        ) from exc
    return wordnet, word_tokenize, pos_tag


def get_wordnet_pos(treebank_tag: str, wordnet: Any | None = None) -> str:
    if wordnet is None:
        wordnet, _, _ = _load_nltk()

    prefixes = {
        "J": wordnet.ADJ,
        "V": wordnet.VERB,
        "N": wordnet.NOUN,
        "R": wordnet.ADV,
    }
    return prefixes.get(treebank_tag[:1], "")


def generate_synonyms(phrase: str, k: int) -> list[str]:
    wordnet, word_tokenize, pos_tag = _load_nltk()
    try:
        words_pos = pos_tag(word_tokenize(phrase))
    except LookupError as exc:
        raise RuntimeError(
            "NLTK tokenizer, tagger, and WordNet data are required for expansion. "
            "See the README for the nltk.download commands."
        ) from exc

    synonyms: list[list[str]] = []
    for word, pos in words_pos:
        candidates: dict[str, float] = {word: 1.0}
        wn_pos = get_wordnet_pos(pos, wordnet)
        synsets = wordnet.synsets(word, pos=wn_pos) if wn_pos else []
        if synsets:
            original = synsets[0]
            for synset in synsets:
                similarity = original.path_similarity(synset) or 0.0
                for lemma in synset.lemmas():
                    candidate = lemma.name().replace("_", " ")
                    candidates[candidate] = max(candidates.get(candidate, 0.0), similarity)

        ranked = sorted(candidates, key=candidates.get, reverse=True)[:k]
        synonyms.append(ranked)

    return [" ".join(words) for words in itertools.product(*synonyms)]


def translate_query(
    tokenizer: Any,
    model: Any,
    query: str,
    languages: tuple[str, ...] = ("French", "German", "Romanian"),
) -> dict[str, str]:
    translations = {"English": query}
    for language in languages:
        inputs = tokenizer(
            f"translate English to {language}: {query}",
            return_tensors="pt",
            padding=True,
        )
        output_sequences = model.generate(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            do_sample=False,
        )
        translations[language] = tokenizer.batch_decode(
            output_sequences,
            skip_special_tokens=True,
        )[0]
    return translations
