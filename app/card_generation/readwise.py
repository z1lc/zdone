from typing import List

import genanki

from app.card_generation.highlight_clozer import get_clozed_highlight
from app.card_generation.util import zdNote, get_rs_anki_css, get_default_css, get_template, AnkiCard
from app.util import JsonDict

READWISE_HIGHLIGHT_CLOZE_MODEL_ID = 1604800000000


def get_highlight_model(user):
    templates: List[JsonDict] = [
        get_template(AnkiCard.READWISE_HIGHLIGHT_CLOZE, user)
    ]
    return genanki.Model(
        # the legacy model ID was from when I imported my model to everyone else. I migrated to the publicly-facing,
        # default model ID, but kept existing users on my old model ID for simplicity.
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


def get_highlights(user):
    # TODO: actually implement the SQL queries and return highlight info
    # select highlights, title, author from readwise_highlights rh [some join type] managed_readwise_books mrb
    # ON rh.managed_book_readwise_book_id = mrb.id AND mrb.user_id = user.id
    # or something like that (needs to incorporate readwise_books table as well somehow)
    # for now, just return a simple list with one highlight (as a dictionary)
    return [{
        'text': 'The most important technique for achieving deep modules is information hiding.',
        'source_title': 'A Philosophy of Software Design',
        'source_author': 'John Ousterhout'}]

def generate_readwise_highlight_clozes(user, deck, tags):
    for highlight in get_highlights(user):
        highlight_text = highlight['text']
        clozed_highlight = get_clozed_highlight(highlight_text)
        highlight_source_title = highlight['source_title']
        highlight_source_author = highlight['source_author']
        highlight_as_note = ReadwiseHighlightClozeNote(
            model=get_highlight_model(user),
            tags=tags,
            fields=[
                clozed_highlight,
                highlight_source_title,
                highlight_source_author])
        deck.add_note(highlight_as_note)


class ReadwiseHighlightClozeNote(zdNote):
    # this more-extended version of guid methods is necessary to provide the legacy guid behavior
    @property
    def guid(self):
        if self._guid is None:
            # TODO: rob, will this be correct if the highlight text is first field? Just need sanity check
            return genanki.guid_for(self.fields[0])
        return self._guid

    @guid.setter
    def guid(self, val):
        self._guid = val


def generate_tracks(user: User, deck: Deck, tags: List[str]):

    for track in get_tracks(user):
        inner_artists = []
        for inner_artist in track['artists']:
            inner_artists.append(inner_artist['name'])
        album_name = track['album']['name'].replace('"', '\'')
        release_year = parser.parse(track['album']['release_date']).date().year
        track_as_note = ReadwiseHighlightClozeNote(
            model=get_track_model(user),
            tags=tags,
            fields=[
                track['uri'],
                track['name'].replace('"', '\''),
                ", ".join(inner_artists).replace('"', '\''),
                f"<i>{album_name}</i> ({release_year})",
                f"<img src='{track['album']['images'][0]['url']}'>"
            ])
        if track['uri'] in legacy_mappings:
            track_as_note.guid = legacy_mappings.get(track['uri'])
        deck.add_note(track_as_note)