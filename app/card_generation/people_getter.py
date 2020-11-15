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
    doc = NLP(highlight)
    return [Person(ent.text) for ent in doc.ents if ent.label_ == "PERSON"]


def _get_wiki_page(name: str) -> Optional[WikipediaPage]:
    try:
        if not wikipedia.search(name):
            # probably a typo, try with auto-suggest
            return wikipedia.page(name, auto_suggest=True)
        else:
            # force no auto suggest
            return wikipedia.page(name, auto_suggest=False)
    except Exception as e:
        log(f"Failed to find person in Wikipedia for: {Person.name}")
        capture_exception(e)
        return None


def _remove_parens_content_except_dates(sentence: str) -> str:
    return re.sub("\(([\w\d \"\-]{1,3}|[\w\d \"]{5,}?)\)", "", sentence)


def _remove_sentence_starters(sentence):
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


def _remove_jr_sr(summary: str) -> str:
    no_jr = summary.replace('Jr.', '')
    no_jr_no_sr = no_jr.replace('Sr.', '')
    return no_jr_no_sr


# In a Wikipedia summary, the person's name may be referenced throughout the sentences. For exmaple, from LeBron's page
# "Widely considered one of the greatest NBA players, James is frequently compared to Michael Jordan in debates over the
# greatest basketball player of all time."
# Note, the use of "James" here. We don't want any references to any part of LeBron's name in the "known for" section,
# so this function removes all references to the person's name in the summary sentence
def _remove_name_refs(sentence: str, name: str) -> str:
    name_parts = name.split(" ")
    result = sentence
    for part in name_parts:
        result = result.replace(part, '')
    return result


def _remove_double_spaces(sentence):
    return sentence.replace('  ', ' ')


def _get_known_for_html(summary_text: str, name: str) -> str:
    print(summary_text)
    summary_no_jr_sr = _remove_jr_sr(summary_text)  # Jr. and Sr. cause problems when splitting on "."
    sentences = summary_no_jr_sr.split(". ")[0:3]
    sentences = [_remove_name_refs(sentence, name) for sentence in sentences]
    sentences = [_remove_parens_content_except_dates(sentence) for sentence in sentences]
    sentences = [_remove_sentence_starters(sentence) for sentence in sentences]
    sentences = [_remove_double_spaces(sentence) for sentence in sentences]
    return "<ul>\n" + \
           "\n".join(["<li>" + sentence.strip() + "</li>" for sentence in sentences]) + \
           "</ul>"


def get_wikipedia_info(person: Person) -> Optional[WikipediaPerson]:
    wiki_page = _get_wiki_page(person.name)
    if not wiki_page:
        return None

    return WikipediaPerson(
        name=wiki_page.title,
        known_for_html=_get_known_for_html(wiki_page.summary, wiki_page.title),
    )
