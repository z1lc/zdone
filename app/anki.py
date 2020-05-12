from enum import Enum
from typing import Dict, List, Optional

import genanki
from genanki import Model, Deck
from jinja2 import Environment, PackageLoader, select_autoescape, StrictUndefined, TemplateNotFound
from jsmin import jsmin

from app.models import LegacySpotifyTrackNoteGuidMapping, SpotifyArtist, User
from app.spotify import get_tracks, get_followed_managed_spotify_artists_for_user
from app.util import JsonDict

SPOTIFY_TRACK_MODEL_ID: int = 1586000000000
SPOTIFY_ARTIST_MODEL_ID: int = 1587000000000
SPOTIFY_TRACK_DECK_ID: int = 1586000000000

"""
Things to keep in mind when adding new models / templates:
(to avoid "Notes that could not be imported as note type has changed" on Anki import)
 * you can change the qfmt and afmt of a template, as long as the template name stays the same
 * you cannot change the names or total count of templates in a model
 * you cannot change the names or total count of fields in a model

A general, long-term approach to avoiding compatibility problems:
 * Create many more fields than you're going to need at the beginning, naming them something unique (maybe adjectives?).
   You're going to re-purpose these fields later for new fields that you'll need.
 * Create many more templates than you need, again naming them something unique. This is again so that you can re-
   purpose later, though you need to make sure cards are not generated in advance for these empty placeholder templates.
   What you can do to make sure this is the case is by making the qfmt and afmt dependent on an unused field, and then 
   later editing that qfmt and afmt to whatever you want. You need to create a field that you never intend to use, 
   perhaps as the last field in the model, in order to assure the conditional card generation works over time.
 * When you want to add a new field and/or template, ensure you DO NOT CHANGE THE NAME, ORDERING, OR TOTAL COUNT.
   If you do, you will cause a permanent backwards incompatibility. Use the unique field names you created in the
   beginning in the unique template names (also created in v1 of the model). This sucks, since your field isn't going 
   to make sense to people looking at the note type, but it is the way it must be if we want to assure compatibility
   over time.

Docs above based on local testing by messing with template & field names, using forked genanki version at 
https://github.com/z1lc/genanki. See https://gist.github.com/z1lc/544a971164bf6179655a869e1f3c3980 for one of the
versions of the code (edited it multiple times & tried importing to test functionality)
"""

env: Environment = Environment(
    loader=PackageLoader('app', 'anki_templates'),
    autoescape=select_autoescape(['html', 'xml']),
    undefined=StrictUndefined
)


# DO NOT CHANGE THESE ENUM NAMES or you will cause backwards incompatibility: the names are used as template names
class AnkiCard(Enum):
    # Spotify Track model
    AUDIO_TO_ARTIST = (1, 'spotify_track')
    AUDIO_AND_ALBUM_ART_TO_ALBUM = (2, 'spotify_track')  # only used by me, not externally

    # Spotify Artist model
    IMAGE_TO_NAME = (3, 'spotify_artist')
    NAME_TO_IMAGE = (4, 'spotify_artist')
    NAME_AND_IMAGE_TO_SONG = (5, 'spotify_artist')
    SONGS_TO_NAME = (6, 'spotify_artist')
    NAME_AND_IMAGE_TO_GENRES = (7, 'spotify_artist')
    NAME_AND_IMAGE_TO_SIMILAR_ARTISTS = (8, 'spotify_artist')
    NAME_AND_IMAGE_TO_YEARS_ACTIVE = (9, 'spotify_artist')
    EXTRA_ARTIST_TEMPLATE_1 = (10, 'spotify_artist')
    EXTRA_ARTIST_TEMPLATE_2 = (11, 'spotify_artist')
    EXTRA_ARTIST_TEMPLATE_3 = (12, 'spotify_artist')
    EXTRA_ARTIST_TEMPLATE_4 = (13, 'spotify_artist')
    EXTRA_ARTIST_TEMPLATE_5 = (14, 'spotify_artist')
    EXTRA_ARTIST_TEMPLATE_6 = (15, 'spotify_artist')
    EXTRA_ARTIST_TEMPLATE_7 = (16, 'spotify_artist')
    EXTRA_ARTIST_TEMPLATE_8 = (17, 'spotify_artist')
    EXTRA_ARTIST_TEMPLATE_9 = (18, 'spotify_artist')
    EXTRA_ARTIST_TEMPLATE_10 = (19, 'spotify_artist')

    def __init__(self, unique_number, directory):
        self.unique_number = unique_number
        self.directory = directory

    def get_template_name(self) -> str:
        return self.name \
            .replace('_', ' ') \
            .title() \
            .replace('To', '>') \
            .replace('And', '+') \
            .replace(' ', '')


class SpotifyTrackNote(genanki.Note):
    # this more-extended version of guid methods is necessary to provide the legacy guid behavior
    @property
    def guid(self):
        if self._guid is None:
            return genanki.guid_for(self.fields[0])
        return self._guid

    @guid.setter
    def guid(self, val):
        self._guid = val


class SpotifyArtistNote(genanki.Note):
    @property
    def guid(self):
        return genanki.guid_for(self.fields[0])


def generate_track_apkg(user: User, filename: str) -> None:
    deck: Deck = Deck(
        SPOTIFY_TRACK_DECK_ID,
        'Spotify Tracks')
    track_model: Model = get_track_model(user)
    artist_model: Model = get_artist_model(user)
    legacy_mappings: Dict[str, str] = {lm.spotify_track_uri: lm.anki_guid for lm in
                                       LegacySpotifyTrackNoteGuidMapping.query.filter_by(user_id=user.id).all()}

    for track in get_tracks(user):
        inner_artists = []
        for inner_artist in track['artists']:
            inner_artists.append(inner_artist['name'])
        track_as_note = SpotifyTrackNote(
            model=track_model,
            fields=[
                track['uri'],
                track['name'].replace('"', '\''),
                ", ".join(inner_artists).replace('"', '\''),
                track['album']['name'].replace('"', '\''),
                "<img src='" + track['album']['images'][0]['url'] + "'>"
            ])
        if track['uri'] in legacy_mappings:
            track_as_note.guid = legacy_mappings.get(track['uri'])
        deck.add_note(track_as_note)

    # released to nobody for now since have to consider backwards-compatibility
    if user.id <= 1:
        for managed_artist in get_followed_managed_spotify_artists_for_user(user, False):
            artist: SpotifyArtist = SpotifyArtist.query.filter_by(uri=managed_artist.spotify_artist_uri).one()
            img_src: Optional[str]
            if artist.good_image and artist.spotify_image_url:
                img_src = artist.spotify_image_url
            elif artist.image_override_name:
                img_src = f"https://www.zdone.co/static/images/artists/{artist.image_override_name}"
            else:
                img_src = None
            if img_src:
                artist_as_note = SpotifyArtistNote(
                    model=artist_model,
                    fields=[
                        artist.uri,
                        artist.name,
                        f"<img src='{img_src}'>",
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                    ])
                deck.add_note(artist_as_note)
    genanki.Package(deck).write_to_file(filename)


def get_artist_model(user: User) -> Model:
    return genanki.Model(
        SPOTIFY_ARTIST_MODEL_ID,
        'Spotify Artist',
        fields=[
            {'name': 'Artist URI'},
            {'name': 'Name'},
            {'name': 'Image'},
            {'name': 'Songs'},
            {'name': 'Albums'},
            {'name': 'Genres'},
            {'name': 'Similar Artists'},
            {'name': 'Years Active'},
            {'name': 'Extra Field 1'},  # Reserved for future use
            {'name': 'Extra Field 2'},  # Reserved for future use
            {'name': 'Extra Field 3'},  # Reserved for future use
            {'name': 'Extra Field 4'},  # Reserved for future use
            {'name': 'Extra Field 5'},  # Reserved for future use
            {'name': 'Extra Field 6'},  # Reserved for future use
            {'name': 'Extra Field 7'},  # Reserved for future use
            {'name': 'Extra Field 8'},  # Reserved for future use
            {'name': 'Extra Field 9'},  # Reserved for future use
            {'name': 'Extra Field 10'},  # Reserved for future use
        ],
        css=get_rs_anki_css() if user.uses_rsAnki_javascript else get_default_css(),
        templates=[
            get_template(AnkiCard.IMAGE_TO_NAME, user),
            get_template(AnkiCard.NAME_TO_IMAGE, user),
            get_template(AnkiCard.NAME_AND_IMAGE_TO_SONG, user),
            get_template(AnkiCard.SONGS_TO_NAME, user),
            get_template(AnkiCard.NAME_AND_IMAGE_TO_GENRES, user),
            get_template(AnkiCard.NAME_AND_IMAGE_TO_SIMILAR_ARTISTS, user),
            get_template(AnkiCard.NAME_AND_IMAGE_TO_YEARS_ACTIVE, user),
            get_template(AnkiCard.EXTRA_ARTIST_TEMPLATE_1, user),
            get_template(AnkiCard.EXTRA_ARTIST_TEMPLATE_2, user),
            get_template(AnkiCard.EXTRA_ARTIST_TEMPLATE_3, user),
            get_template(AnkiCard.EXTRA_ARTIST_TEMPLATE_4, user),
            get_template(AnkiCard.EXTRA_ARTIST_TEMPLATE_5, user),
            get_template(AnkiCard.EXTRA_ARTIST_TEMPLATE_6, user),
            get_template(AnkiCard.EXTRA_ARTIST_TEMPLATE_7, user),
            get_template(AnkiCard.EXTRA_ARTIST_TEMPLATE_8, user),
            get_template(AnkiCard.EXTRA_ARTIST_TEMPLATE_9, user),
            get_template(AnkiCard.EXTRA_ARTIST_TEMPLATE_10, user),
        ]
    )


def get_track_model(user: User) -> Model:
    should_generate_albumart_card: bool = user.username == "rsanek"
    legacy_model_id: int = 1579060616046

    templates: List[JsonDict] = [
        get_template(AnkiCard.AUDIO_TO_ARTIST, user)
    ]
    if should_generate_albumart_card:
        templates.append(get_template(AnkiCard.AUDIO_AND_ALBUM_ART_TO_ALBUM, user))

    return genanki.Model(
        # the legacy model ID was from when I imported my model to everyone else. I migrated to the publically-facing,
        # default model ID, but kept existing users on my old model ID for simplicity.
        legacy_model_id if 1 < user.id <= 6 else SPOTIFY_TRACK_MODEL_ID,
        'Spotify Track',
        fields=[
            {'name': 'Track URI'},
            {'name': 'Track Name'},
            {'name': 'Artist(s)'},
            {'name': 'Album'},
            {'name': 'Album Art'},
        ],
        css="@import '_anki.css';" if user.uses_rsAnki_javascript else get_default_css(),
        templates=templates
    )


def get_template(card_type: AnkiCard, user: User) -> JsonDict:
    rs_anki_enabled: bool = user.uses_rsAnki_javascript
    api_key: str = user.api_key
    return {
        'name': card_type.get_template_name(),
        'qfmt': render_front(card_type, api_key, rs_anki_enabled),
        'afmt': render_back(card_type, api_key, rs_anki_enabled),
    }


def render_template(card_type: AnkiCard, is_front: bool, api_key: str, rs_anki_enabled: bool) -> str:
    script_include = get_rs_anki_custom_script() if rs_anki_enabled else get_default_script()
    if is_front and card_type in [AnkiCard.AUDIO_TO_ARTIST, AnkiCard.AUDIO_AND_ALBUM_ART_TO_ALBUM]:
        script_include += f"""<script type="text/javascript">
{get_minified_js_for_song_jump(api_key)}
</script>"""
    try:
        return env.get_template(card_type.directory + '/' + card_type.name.lower() + '.html') \
            .render(is_front=is_front, script_include=script_include)
    except TemplateNotFound as e:
        # don't require us to write blank HTML templates for the extras if we don't want to
        if "extra" in card_type.name.lower():
            return ""
        raise e


def render_back(card_type: AnkiCard, api_key: str, rs_anki_enabled: bool) -> str:
    return render_template(card_type, False, api_key, rs_anki_enabled)


def render_front(card_type: AnkiCard, api_key: str, rs_anki_enabled: bool) -> str:
    return render_template(card_type, True, api_key, rs_anki_enabled)


def get_minified_js_for_song_jump(api_key: str) -> str:
    return jsmin(f"""
function pr(data) {{
  if (typeof data.reason !== 'undefined') {{
    $("#error").html(data.reason);
    $("#jump").val('Resume Playback');
  }} else {{
    $("#error").html('');
    $("#jump").val('Jump to Random Location');
  }}
}}
function jump() {{
  $.getScript("https://www.zdone.co/api/{api_key}/play/{{{{Track URI}}}}/pr");
}};
jump();
$(document).keypress(function(e) {{
    if (e.key === 'r' || e.key === 'R') {{
        jump();
    }}
}});
""")


def get_rs_anki_custom_script() -> str:
    return """<script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/latest.js?config=TeX-AMS_CHTML"></script>
<script type="text/javascript" src="_jquery-1.11.2.min.js"></script>
<div id="categoryIdentifierFront">{{Tags}}</div>
<script type="text/javascript" src="_AnkiLibrary.js"></script>
<script type="text/javascript">if (typeof rsAnki !== 'undefined') rsAnki.defaultUnified();</script>"""


def get_default_script() -> str:
    return """<script type="text/javascript" src="https://code.jquery.com/jquery-1.12.4.min.js"></script>"""


def get_rs_anki_css() -> str:
    return """@import '_anki.css';

#jump {
  font-size: 24px;
}"""


def get_default_css() -> str:
    return """.card {
  background: white;
  font-size: 24px;
  text-align: center;
}

hr {
  height: 1px;
  margin: 20px 0;
  background-color: black;
  border: none;
}

ol, ul {
  text-align: left;
  display: inline-block;
  margin-left: 30px;
  margin-top: 0px;
}

.rsAnswer {
  color: blue;
  font-weight: bold;
}

img {
  max-width: 100%;
}

#jump {
  font-size: 24px;
}"""
