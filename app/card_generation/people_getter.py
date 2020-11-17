import re
from datetime import timedelta
from typing import List, Optional, Dict

import genanki
import spacy
from sentry_sdk import capture_exception
from wikipedia import wikipedia, WikipediaPage, PageError, WikipediaException

from app.card_generation.util import zdNote, get_template, AnkiCard, get_rs_anki_css, get_default_css
from app.log import log
from app.util import JsonDict

NLP = spacy.load("en_core_web_sm")
PERSON_MODEL_ID = 1605000000000
wikipedia.set_rate_limiting(True, timedelta(seconds=1))


class Person:

    def __init__(self, name: str, seen_in: str, selected_highlight: str):
        self.name = name
        self.seen_in = seen_in
        self.selected_highlight = selected_highlight

    def __eq__(self, other):
        return isinstance(other, Person) and other.name == self.name

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return "Person(" + self.name + ")"


class WikipediaPerson(Person):

    def __init__(self, name: str, seen_in: str, selected_highlight: str, known_for_html: str, images: str):
        super().__init__(name, seen_in, selected_highlight)
        self.known_for_html = known_for_html
        self.images = images

    def __repr__(self):
        return f"WikipediaPerson(name={self.name}, known_for_html={self.known_for_html}, highlight={self.selected_highlight})"


def _looks_like_name(text: str) -> bool:
    return re.fullmatch(r"([A-Z]([\.a-z])+[ ]?)+", text) is not None


def get_people(highlight_data: Dict[str, str]) -> List[Person]:
    doc = NLP(highlight_data['text'])
    return [Person(ent.text, highlight_data['source_title'], highlight_data['text']) for ent in doc.ents if
            _looks_like_name(ent.text) and
            ent.label_ in ["PERSON"]]


def get_person_note(wikipedia_person: WikipediaPerson, tags, user):
    return zdNote(
        model=_get_person_model(user),
        tags=tags,
        fields=[
            wikipedia_person.name,
            wikipedia_person.known_for_html,
            wikipedia_person.images,
            wikipedia_person.seen_in,
            wikipedia_person.selected_highlight
        ])


def _get_person_model(user):
    templates: List[JsonDict] = [
        get_template(AnkiCard.PERSON_NAME_TO_IMAGE, user),
        get_template(AnkiCard.PERSON_IMAGE_TO_NAME, user),
        get_template(AnkiCard.PERSON_KNOWN_FOR_TO_NAME_AND_IMAGE, user),
    ]
    return genanki.Model(
        PERSON_MODEL_ID,
        'Notable Person',
        fields=[
            {'name': 'Name'},
            {'name': 'Known For'},
            {'name': 'Image'},
            {'name': 'Seen In'},
            {'name': 'Selected Highlight'}
            # TODO(rob/will): Add more fields before public release
        ],
        css=(get_rs_anki_css() if user.uses_rsAnki_javascript else get_default_css()),
        templates=templates,
    )


def _get_wiki_page(name: str) -> Optional[WikipediaPage]:
    try:
        if not wikipedia.search(name):
            # no pages with this name
            return None
        return wikipedia.page(name, auto_suggest=False)
    except WikipediaException as e:
        log(f"Failed to find person in Wikipedia for: {name}")
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
    summary_no_jr_sr = _remove_jr_sr(summary_text)  # Jr. and Sr. cause problems when splitting on "."
    sentences = summary_no_jr_sr.split(". ")[0:3]
    sentences = [_remove_name_refs(sentence, name) for sentence in sentences]
    sentences = [_remove_parens_content_except_dates(sentence) for sentence in sentences]
    sentences = [_remove_sentence_starters(sentence) for sentence in sentences]
    sentences = [_remove_double_spaces(sentence) for sentence in sentences]
    return "<ul>\n" + \
           "\n".join(["<li>" + sentence.strip() + "</li>" for sentence in sentences]) + \
           "</ul>"


def _get_images_with_persons_name(image_urls: List[str], name: str) -> List[str]:
    first_name = name.split(" ")[0]
    return list(filter(lambda url: first_name.lower() in url.lower(), image_urls))


def _get_image_html(image_urls: List[str], name: str) -> str:
    relevant_image_urls = _get_images_with_persons_name(image_urls, name)[0:3]
    return "".join([f"<img src=\"{url}\">" for url in relevant_image_urls])


def get_wikipedia_info(person: Person) -> Optional[WikipediaPerson]:
    wiki_page = _get_wiki_page(person.name)
    if not wiki_page:
        return None

    name_on_wikipedia = wiki_page.title
    return WikipediaPerson(
        name=wiki_page.title,
        seen_in=person.seen_in,
        selected_highlight=person.selected_highlight,
        known_for_html=_get_known_for_html(wiki_page.summary, name_on_wikipedia),
        images=_get_image_html(wiki_page.images, name_on_wikipedia))
