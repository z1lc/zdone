import random
import re
import string
from typing import List, Tuple

import spacy
from spacy.tokens import Span
from spacy_langdetect import LanguageDetector

from app.config import is_prod

NLPs = None
BORING_WORDS = [
    "they",
    "them",
    "one",
    "two",
    "it",
    "we",
    "you",
    "i",
    "me",
    "what",
    "people",
    "person",
    "chapter",
    "reason",
    "why",
    "who",
    "when",
    "where",
    "something",
    "alternative",
]


def get_NLPs():
    global NLPs
    if not NLPs:
        en = spacy.load("en_core_web_sm")
        en.add_pipe(LanguageDetector(), name="language_detector", last=True)
        NLPs = {
            "en": en,
            "fr": spacy.load("fr_core_news_sm"),
            "es": spacy.load("es_core_news_sm"),
            "cs": spacy.blank("cs"),  # no Czech models yet
        }
    return NLPs


def get_clozed_highlight_and_keyword(highlight) -> Tuple[str, str]:
    # use basic nlp to identify keyword in sentence to cloze
    keywords = get_keywords(highlight)
    random_keyword = random.choice(keywords) if is_prod() and detect_language(highlight) == "en" else keywords[0]
    return cloze_out_keyword(random_keyword, highlight), random_keyword


# Returns a word with punctuation chars removed, except dashes in middle of word
# ham, -> ham
# extra-crispy -> extra-crispy
# Mexico's -> Mexico
def no_punc(word: str) -> str:
    word_apostrophe_removed = re.sub(r"'.", "", word)
    return word_apostrophe_removed.strip(string.punctuation)


# returns a list of keywords for a given sentence
# currently, the list only ever has a single item, because the input sentences are not intended for
# super long term retention. This can be configured
# Returned keywords should not have punctuation
def get_longest_word(no_punctuation_sentence) -> str:
    return max(no_punctuation_sentence.split(" "), key=len)


def detect_language(sentence: str) -> str:
    return get_NLPs()["en"](sentence)._.language["language"]


# Takes a word and attempts to return a simple lemma of the word.
# This involves removing punctuation in the word along with attempting to convert the word from plural to singular form
# We could use spacy here, but that seemed like overkill given the majority of what we are trying to do can be
# accomplished by just removing trailing "s" characters from words.
# Example transformations:
# words. -> word
# apples! -> apple
# examples, -> example
# Mexico's -> Mexico
def _lemmatized(text):
    return no_punc(text).rstrip("s")


def get_keywords(sentence: str) -> List[str]:
    # try to get language-specific NLP, but fall back to English if we don't have one for that language
    doc = get_NLPs().get(detect_language(sentence), get_NLPs()["en"])(sentence)
    result = set()
    # first, grab interesting entities. will include things like "LeBron James", "Google", and "1865" (year)
    result.update(get_interesting_entities(doc.ents))
    # next, add worthwhile nouns like "dog", "fox"
    result.update(
        [
            _lemmatized(noun_chunk.root.text)
            for noun_chunk in doc.noun_chunks
            if _lemmatized(noun_chunk.root.text).lower() not in BORING_WORDS
        ]
    )
    # finally, let's add the longest word
    result.update([_lemmatized(get_longest_word(no_punc(sentence)))])
    return list(result)


# Highlights will fairly regularly have the structure of
# "One way to do..." or "Two things that differentiate..." etc
# Often, the nlp will recognize "One" and "Two" as entities, which
# can result in them being clozed out. Clozing out cardinal/ordinal entities
# at the front of highlights is almost never useful, so this function helps filter them
# out.
def not_number_at_front(ent):
    return ent.label_ not in ["ORDINAL", "CARDINAL"] or ent.start > 3


# Sometimes the keyword will be something like "the United Kingdom".
# This method takes keywords like that and transforms them into "United Kingdom"
def _clean_keyword(best_entity: str) -> str:
    bad_starting_words = ["the", "a", "an", "of", "on", "in"]
    stripped_best_entity = best_entity.strip()
    best_entity_words = stripped_best_entity.split(" ")
    if best_entity_words[0].lower() in bad_starting_words:
        best_entity_words = best_entity_words[1:]

    # handle any whitespace issues
    result = " ".join(best_entity_words)
    result = result.strip()
    return _lemmatized(result)


# return the most interesting entities from a list of entities in a sentence
# input: tuple of nlp-generated entities from a sentence
# output: list of best entities (currently only ever returns 1 entity)
def get_interesting_entities(all_entities: Tuple[Span]) -> List[str]:
    if not all_entities:
        return []
    interesting_entities = filter(lambda ent: not_number_at_front(ent), all_entities)
    cleaned_interesting_ents = map(lambda ent: _clean_keyword(ent.text), interesting_entities)
    return list(cleaned_interesting_ents)


# returns sentence with all occurrences of keyword clozed out.
# In the case where a keyword contains multiple words ("LeBron James"),
# for simplicity, just remove full instances of the keyword. In case where keyword
# is single word, replaces all occurrences regardless of punctuation/capitalization of word
def cloze_out_keyword(keyword: str, sentence: str) -> str:
    sentence_words = sentence.split(" ")
    num_words_in_keywords = len(keyword.split(" "))
    if num_words_in_keywords > 1:
        return sentence.replace(keyword, cloze_word_with_punc(keyword))
    return " ".join(
        map(
            lambda word: cloze_word_with_punc(word) if _lemmatized(word).lower() == keyword.lower() else word,
            sentence_words,
        )
    )


def get_prefix_punc(word: str) -> str:
    prefix_punc_end_idx = 0
    while prefix_punc_end_idx < len(word) and word[prefix_punc_end_idx] in string.punctuation:
        prefix_punc_end_idx += 1
    return word[:prefix_punc_end_idx]


def get_suffix_punc(word: str) -> str:
    last_non_punc_idx = len(word) - 1
    while last_non_punc_idx >= 0 and word[last_non_punc_idx] in string.punctuation:
        last_non_punc_idx -= 1
    # check for apostrophes in possessive/plurals prior to other punctuation
    # e.g. catch things like "The house is LeBron's."
    trimmed_ending_punctuation_word = word[: last_non_punc_idx + 1]
    if trimmed_ending_punctuation_word.endswith("'s"):
        last_non_punc_idx -= 2  # trim 's
    return word[last_non_punc_idx + 1 :]


def cloze_word_with_punc(word: str, idx: int = 0) -> str:
    prefix_punc = get_prefix_punc(word)
    suffix_punc = get_suffix_punc(word)
    return prefix_punc + "{{c" + str(idx + 1) + "::" + no_punc(word) + "}}" + suffix_punc
