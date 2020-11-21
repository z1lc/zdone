from itertools import groupby
from typing import List

import genanki
from genanki import Deck

from app import db
from app.card_generation.highlight_clozer import get_clozed_highlight
from app.card_generation.people_getter import get_people, get_wikipedia_info, get_person_note
from app.card_generation.util import zdNote, get_rs_anki_css, get_default_css, get_template, AnkiCard
from app.log import log
from app.models.base import User
from app.util import JsonDict

READWISE_HIGHLIGHT_CLOZE_MODEL_ID = 1604800000000


def generate_readwise_people(user: User, deck: Deck, tags: List[str]):
    if not user.id == 2:
        log("Generating people cards from highlights is not enabled for this user yet")
        return

    highlights = get_highlights(user)
    notes = _get_person_notes_from_highlight(highlights, tags, user)
    for note in notes:
        deck.add_note(note)
    log(f"Completed person generation for {user.username}. Found {len(notes)} people in highlights")


def _get_person_notes_from_highlight(highlights, tags, user):
    all_people = []
    for highlight in highlights:
        people_in_highlight = get_people(highlight)
        all_people += people_in_highlight
    # use set here to deduplicate people after searching through wikipedia. Will ensure that
    # Person(Lincoln) and Person(Abraham Lincoln) result in one copy of WikipediaPerson(Abraham Lincoln)
    maybe_wikipedia_people = set([get_wikipedia_info(person) for person in all_people])
    return [get_person_note(wikipedia_person, tags, user) for wikipedia_person in maybe_wikipedia_people if
            wikipedia_person]


def get_highlight_model(user: User):
    templates: List[JsonDict] = [
        get_template(AnkiCard.HIGHLIGHT_CLOZE_1, user)
    ]
    return genanki.Model(
        READWISE_HIGHLIGHT_CLOZE_MODEL_ID,
        'Readwise Highlight',
        fields=[
            {'name': 'zdone Highlight ID'},
            {'name': 'Original Highlight'},
            {'name': 'Clozed Highlight'},
            {'name': 'Source Title'},
            {'name': 'Source Author'},
            {'name': 'Image'},
            {'name': 'Prev Highlight'},
            {'name': 'Next Highlight'},
            # TODO(rob/will): Add more fields before public release
        ],
        css=(get_rs_anki_css() if user.uses_rsAnki_javascript else get_default_css()),
        templates=templates,
        model_type=genanki.Model.CLOZE
    )


def get_highlights(user: User):
    prepared_sql = f"""
        select rh.id, text, title, author, cover_image_url
        from readwise_books b
            join managed_readwise_books mrb on b.id = mrb.readwise_book_id
            join readwise_highlights rh on mrb.id = rh.managed_readwise_book_id
        where mrb.user_id = {user.id}
        order by mrb.id asc, rh.id asc
    """
    highlights = list(db.engine.execute(prepared_sql))
    return [{
        'id': highlight[0],
        'text': highlight[1],
        'source_title': highlight[2],
        'source_author': highlight[3],
        'cover_image_url': highlight[4]} for highlight in highlights]


def group_highlights_by_book(all_highlights):
    keyFunc = lambda highlight: highlight['source_title']
    all_highlights_sorted = sorted(all_highlights, key=keyFunc)
    return groupby(all_highlights_sorted, keyFunc)


def generate_readwise_highlight_clozes(user: User, deck: Deck, tags: List[str]):
    all_highlights = get_highlights(user)
    clozed_highlight_notes = _generate_clozed_highlight_notes(all_highlights, tags, user)
    for note in clozed_highlight_notes:
        deck.add_note(note)


# Given highlights from db, return cloze notes for those highlights
# Useful as testing seam for entire cloze generation pipeline without hitting real db
def _generate_clozed_highlight_notes(all_highlights, tags, user):
    # Don't produce cloze cards for highlights that only contain a small number of words
    long_enough_highlights = list(filter(lambda highlight: len(highlight['text'].split(" ")) > 5, all_highlights))
    result = []
    grouped_highlights = group_highlights_by_book(long_enough_highlights)
    for book, book_highlights in grouped_highlights:
        # convert to list to use indexing for prev/next highlight
        book_highlights_list = list(book_highlights)
        for i in range(len(book_highlights_list)):
            highlight_i = book_highlights_list[i]
            maybe_clozed_highlight = get_clozed_highlight(highlight_i['text'])
            if '{{c1::' in maybe_clozed_highlight:
                highlight_i['clozed_highlight'] = maybe_clozed_highlight
                if i > 0:
                    highlight_i['prev_highlight'] = book_highlights_list[i - 1]['text']
                else:
                    highlight_i['prev_highlight'] = ""
                if i < len(book_highlights_list) - 1:
                    highlight_i['next_highlight'] = book_highlights_list[i + 1]['text']
                else:
                    highlight_i['next_highlight'] = ""

                highlight_i['image'] = ""
                # image sources that are on Readwise's S3 bucket are generally not useful
                if 'readwise-assets' not in highlight_i['cover_image_url']:
                    highlight_i['image'] = f"<img src='{highlight_i['cover_image_url']}'>"
                highlight_as_note = zdNote(
                    model=get_highlight_model(user),
                    tags=tags,
                    fields=[
                        highlight_i['id'],
                        highlight_i['text'],
                        highlight_i['clozed_highlight'],
                        highlight_i['source_title'],
                        highlight_i['source_author'],
                        highlight_i['image'],
                        highlight_i['prev_highlight'],
                        highlight_i['next_highlight']
                    ])
                result += [highlight_as_note]
    return result
