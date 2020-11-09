from genanki import Deck
from typing import List

import genanki

from app import db
from app.card_generation.highlight_clozer import get_clozed_highlight
from app.card_generation.util import zdNote, get_rs_anki_css, get_default_css, get_template, AnkiCard
from app.models.base import User
from app.util import JsonDict

READWISE_HIGHLIGHT_CLOZE_MODEL_ID = 1604800000000


def get_highlight_model(user: User):
    templates: List[JsonDict] = [
        get_template(AnkiCard.READWISE_HIGHLIGHT_CLOZE, user)
    ]
    return genanki.Model(
        READWISE_HIGHLIGHT_CLOZE_MODEL_ID,
        'Readwise Highlight',
        fields=[
            {'name': 'Text'},
            {'name': 'Source Title'},
            {'name': 'Source Author'},
            {'name': 'Prev Highlight'},
            {'name': 'Next Highlight'},
            # TODO(rob/will): Add more fields before public release
        ],
        css=(get_rs_anki_css() if user.uses_rsAnki_javascript else get_default_css()),
        templates=templates)


def get_highlights(user: User):
    # TODO: actually implement the SQL queries and return highlight info
    prepared_sql = f"""
    SELECT the_highlights.text, books.title, books.author FROM readwise_books as books 
        INNER JOIN (SELECT rh.text as text, mrb.readwise_book_id as book_id FROM readwise_highlights rh 
                    INNER JOIN managed_readwise_books mrb 
                    ON rh.managed_readwise_book_id = mrb.id AND mrb.user_id = {user.id}) as the_highlights 
        ON the_highlights.book_id = books.id;
    """
    highlights = list(db.engine.execute(prepared_sql))
    return [{
        'text': highlight[0],
        'source_title': highlight[1],
        'source_author': highlight[2]} for highlight in highlights]

def generate_readwise_highlight_clozes(user: User, deck: Deck, tags: List[str]):
    for highlight in get_highlights(user):
        highlight_text = highlight['text']
        clozed_highlight = get_clozed_highlight(highlight_text)
        highlight_source_title = highlight['source_title']
        highlight_source_author = highlight['source_author']
        highlight_as_note = zdNote(
            model=get_highlight_model(user),
            tags=tags,
            fields=[
                clozed_highlight,
                highlight_source_title,
                highlight_source_author])
        deck.add_note(highlight_as_note)