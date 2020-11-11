import spacy


# initialize the model once when we import this script
NLP = spacy.load("en_core_web_sm")


def get_clozed_highlight(highlight):
    # use basic nlp to identify keyword in sentence to cloze
    keywords = get_keywords(highlight)
    result = highlight  # start with un-clozed sentence as result
    for idx, keyword in enumerate(keywords):
        result = cloze_out_keyword(keyword, idx, result)
    return result


# returns a list of keywords for a given sentence
# currently, the list only ever has a single item, because the input sentences are not intended for
# super long term retention. This can be configured
def get_keywords(sentence):
    doc = NLP(sentence)
    # first see if we have some nice named entities for the cloze
    result = get_best_entities(doc.ents)
    if result:
        # return the first named entity just because multiple clozes in a highlight ends up being a lot of reviewing
        # for a card that probably isn't ideal (even if the cloze's are good, the volume of highlights should be
        # pretty high)
        return result[:1]
    # we didn't find any good entities, so let's just return a core noun from a noun phrase
    for noun_chunk in doc.noun_chunks:
        # don't return bad nouns like "they"
        if is_interesting_noun(noun_chunk.root.text):
            return [noun_chunk.root.text]

    # nothing has worked, so just return whatever word is longest
    return max(sentence.split(" "), key=len)


# return the most interesting entities from a list of entities in a sentence
# input: tuple of nlp-generated entities from a sentence
# output: list of best entities (currently only ever returns 1 entity)
def get_best_entities(ents):
    if len(ents) == 0:
        return []
    # the best entity will likely be repeated many times or just be the first one
    max_count = 0
    best_entity = None
    for ent in ents:
        ent_count = ents.count(ent)
        # this will match the first entitiy that isn't something like "one"
        # also will deliberately not match any entities that are the first word in the sentence, as
        # that makes for a jarring cloze card
        if ent_count > max_count and (ent.label_ not in ["ORDINAL", "CARDINAL"] and ent.start != 0):
            max_count = ent_count
            best_entity = ent.text

    if best_entity is None:
        # make sure to return empty list here
        return []
    return [best_entity]


def is_interesting_noun(text):
    boring_words = ['they', 'them', 'one', 'two', 'it', 'we', 'you', 'i', 'me']
    return text.lower() not in boring_words

# returns sentence with all occurrences of keyword clozed out
# this is case-sensitive for now
def cloze_out_keyword(keyword, idx, sentence):
    sentence_words = sentence.split(" ")
    return " ".join(map(lambda word: cloze_word(idx, word) if word.lower() == keyword.lower() else word, sentence_words))

def cloze_word(idx, word):
    return '{{c' + str(idx + 1) + '::' + word + "}}"
