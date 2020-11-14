import string
from typing import List, Tuple

import spacy

# initialize the model once when we import this script
from spacy.tokens import Doc, Span

NLP = spacy.load("en_core_web_sm")


def get_clozed_highlight(highlight):
    # use basic nlp to identify keyword in sentence to cloze
    keywords = get_keywords(highlight)
    result = highlight  # start with un-clozed sentence as result
    for idx, keyword in enumerate(keywords):
        result = cloze_out_keyword(keyword, idx, result)
    return result


# Returns a word with punctuation chars removed, except dashes in middle of word
# ham, -> ham
# extra-crispy -> extra-crispy
def no_punc(word: str) -> str:
    return word.strip(string.punctuation)


# returns a list of keywords for a given sentence
# currently, the list only ever has a single item, because the input sentences are not intended for
# super long term retention. This can be configured
# Returned keywords should not have punctuation
def get_longest_word(no_punctuation_sentence) -> str:
    return max(no_punctuation_sentence.split(" ", key=len))


def get_keywords(sentence):
    doc = NLP(sentence)
    # first see if we have some nice named entities for the cloze
    result = get_best_entities(doc.ents)
    if result:
        # return the first named entity just because multiple clozes in a highlight ends up being a lot of reviewing
        # for a card that probably isn't ideal (even if the cloze's are good, the volume of highlights should be
        # pretty high)
        return list(no_punc(result[0]))
    # we didn't find any good entities, so let's just return a core noun from a noun phrase
    for noun_chunk in doc.noun_chunks:
        # don't return bad nouns like "they"
        if is_interesting_noun(noun_chunk.root.text):
            return list(no_punc(noun_chunk.root.text))

    # nothing has worked, so just return whatever word is longest
    no_punctuation_sentence = no_punc(sentence)
    return list(get_longest_word(no_punctuation_sentence))


# Highlights will fairly regularly have the structure of
# "One way to do..." or "Two things that differentiate..." etc
# Often, the nlp will recognize "One" and "Two" as entities, which
# can result in them being clozed out. Clozing out cardinal/ordainal entities
# at the front of higlights is almost never useful, so this function helps filter them
# out.
def not_number_at_front(ent):
    return ent.label_ not in ["ORDINAL", "CARDINAL"] and ent.start != 0


# return the most interesting entities from a list of entities in a sentence
# input: tuple of nlp-generated entities from a sentence
# output: list of best entities (currently only ever returns 1 entity)
def get_best_entities(ents: Tuple[Span]):
    if not ents:
        return []
    # the best entity will likely be repeated many times or just be the first one
    max_count = 0
    best_entity = None
    for ent in ents:
        ent_count = ents.count(ent)
        # this will match the first entitiy that isn't something like "one"
        # also will deliberately not match any entities that are the first word in the sentence, as
        # that makes for a jarring cloze card
        if ent_count > max_count and not_number_at_front(ent):
            max_count = ent_count
            best_entity = ent.text

    if best_entity is None:
        # make sure to return empty list here
        return []
    return [best_entity]


def is_interesting_noun(text: str) -> bool:
    boring_words = ['they', 'them', 'one', 'two', 'it', 'we', 'you', 'i', 'me']
    return no_punc(text.lower()) not in boring_words


# returns sentence with all occurrences of keyword clozed out
# this is case-sensitive for now
def cloze_out_keyword(keyword: str, idx: int, sentence: str):
    sentence_words = sentence.split(" ")
    return " ".join(map(lambda word: cloze_word_with_punc(idx, word) if no_punc(word.lower()) == keyword.lower() else word,
                        sentence_words))


def get_prefix_punc(word):
    prefix_punc_end_idx = 0
    while prefix_punc_end_idx < len(word) and word[prefix_punc_end_idx] in string.punctuation:
        prefix_punc_end_idx += 1
    return word[:prefix_punc_end_idx]


def get_suffix_punc(word):
    suffix_punc_start_idx = len(word) - 1
    while suffix_punc_start_idx >= 0 and word[suffix_punc_start_idx] in string.punctuation:
        suffix_punc_start_idx -= 1
    return word[suffix_punc_start_idx + 1:]


def cloze_word_with_punc(idx, word):
    prefix_punc = get_prefix_punc(word)
    suffix_punc = get_suffix_punc(word)
    return prefix_punc + '{{c' + str(idx + 1) + '::' + no_punc(word) + "}}" + suffix_punc
