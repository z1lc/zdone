import re
from typing import List, Optional

import spacy
from sentry_sdk import capture_exception
from wikipedia import wikipedia, WikipediaPage, PageError, WikipediaException

from app.log import log

NLP = spacy.load("en_core_web_sm")


class Person:

    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other):
        return isinstance(other, Person) and other.name == self.name

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return "Person(" + self.name + ")"


class WikipediaPerson(Person):

    def __init__(self, name, known_for_html):
        super().__init__(name)
        self.known_for_html = known_for_html


def get_people(highlight: str) -> List[Person]:
    result = []
    doc = NLP(highlight)
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            result += [Person(ent.text)]
    return result


def get_wiki_page(name: str) -> Optional[WikipediaPage]:
    try:
        if len(wikipedia.search(name)) == 0:
            # probably a typo, try with auto-suggest
            return wikipedia.page(name, auto_suggest=True)
        else:
            # force no auto suggest
            return wikipedia.page(name, auto_suggest=False)
    except Exception as e:
        log("Failed to find person in Wikipedia for: {name}".format(name=Person.name))
        capture_exception(e)
        return None


def remove_parens_content_except_dates(sentence: str) -> str:
    return re.sub("\(([\w\d \"\-]{1,3}|[\w\d \"]{5,}?)\)", "", sentence)


def remove_sentence_starters(sentence):
    sentence_starters = [".*? (is|was|has been|has) (an|a|the) ",
                         ".*? (is|was|has been|has) ",
                         "He (is|was|has been|has) ",
                         "She (is|was|has been|has) ",
                         "They (are|were|have been|has) ",
                         "They're ",
                         "His ",
                         "Her ",
                         "Their "]
    return re.sub("(" + "|".join(sentence_starters) + ")", "", sentence, count=1)


def remove_jr_sr(summary: str) -> str:
    no_jr = summary.replace('Jr.', '')
    no_jr_no_sr = no_jr.replace('Sr.', '')
    return no_jr_no_sr


def remove_name_refs(sentence: str, name: str) -> str:
    name_parts = name.split(" ")
    result = sentence
    for part in name_parts:
        result = result.replace(" " + part, '')
    return result


def remove_double_spaces(sentence):
    return sentence.replace('  ', ' ')


def get_known_for_html(wiki_page: WikipediaPage) -> str:
    summary_no_jr_sr = remove_jr_sr(wiki_page.summary) # Jr. and Sr. cause problems when splitting on "."
    sentences = summary_no_jr_sr.split(". ")[0:3]
    sentences = [remove_name_refs(sentence, wiki_page.title) for sentence in sentences]
    sentences = [remove_parens_content_except_dates(sentence) for sentence in sentences]
    sentences = [remove_sentence_starters(sentence) for sentence in sentences]
    sentences = [remove_double_spaces(sentence) for sentence in sentences]
    return "<ul>\n" + \
           "\n".join(["<li>" + sentence.strip() + "</li>" for sentence in sentences]) + \
           "</ul>"


def get_wikipedia_info(person: Person) -> Optional[WikipediaPerson]:
    wiki_page = get_wiki_page(person.name)
    if not wiki_page:
        return None

    return WikipediaPerson(
        name=wiki_page.title,
        known_for_html=get_known_for_html(wiki_page),
    )
