from typing import List

import genanki
from genanki import Deck

from app.card_generation.spotify import generate_tracks, generate_artists
from app.card_generation.videos import generate_videos
from app.models.base import User

SPOTIFY_TRACK_DECK_ID: int = 1586000000000

"""
Things to keep in mind when adding new models / templates:
(to avoid "Notes that could not be imported as note type has changed" on Anki import)
 * you can change the qfmt and afmt of a template, as long as the template name stays the same
 * you cannot change the names or total count of templates in a model
 * you cannot change the names or total count of fields in a model
See https://anki.tenderapp.com/kb/problems/some-updates-were-ignored-because-note-type-has-changed for details.

A general, long-term approach to avoiding compatibility problems:
 * Create many more fields and templates than you're going to need at the beginning, naming them something unique.
   You're going to re-purpose these empty fields & templates later for new things that you'll want to add.
 * When you want to add a new field and/or template, ensure you DO NOT CHANGE THE NAME, ORDERING, OR TOTAL COUNT.
   If you do, you will cause a permanent backwards incompatibility. Use the unique field names you created in the
   beginning in the unique template names (also created in v1 of the model). This sucks, since your field and template
   names aren't going to make sense to people reading them in the browser / card type editor, but it is the way it must 
   be if we want to assure compatibility over the long term.

Docs above based on local testing by messing with template & field names, using forked genanki version at 
https://github.com/z1lc/genanki. See https://gist.github.com/z1lc/544a971164bf6179655a869e1f3c3980 for one of the
versions of the code (edited it multiple times & tried importing to test functionality).
"""


def generate_full_apkg(user: User, filename: str) -> None:
    deck: Deck = Deck(
        SPOTIFY_TRACK_DECK_ID,
        'Spotify Tracks')
    tags: List[str] = [] if user.default_spotify_anki_tag is None else [user.default_spotify_anki_tag]

    generate_tracks(user, deck, tags)

    # artists released internally only so far
    if user.id <= 6:
        generate_artists(user, deck, tags)

    # videos not released yet
    if user.id <= 1:
        generate_videos(user, deck, tags)

    genanki.Package(deck).write_to_file(filename)