from enum import Enum

import genanki
from jsmin import jsmin

from app.models import LegacySpotifyTrackNoteGuidMapping, SpotifyArtist
from app.spotify import get_tracks, get_followed_managed_spotify_artists_for_user

SPOTIFY_TRACK_MODEL_ID = 1586000000000
SPOTIFY_ARTIST_MODEL_ID = 1587000000000
SPOTIFY_TRACK_DECK_ID = 1586000000000


class AnkiCard(Enum):
    AUDIO_TO_ARTIST = 1
    AUDIO_AND_ALBUMART_TO_ARTIST = 2
    ARTIST_IMAGE_TO_NAME = 3
    ARTIST_NAME_TO_IMAGE = 4


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


def generate_track_apkg(user, filename):
    deck = genanki.Deck(
        SPOTIFY_TRACK_DECK_ID,
        'Spotify Tracks')
    track_model = get_track_model(user)
    artist_model = get_artist_model(user)
    legacy_mappings = {lm.spotify_track_uri: lm.anki_guid for lm in
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

    # internal only release for now
    if user.id <= 6:
        for managed_artist in get_followed_managed_spotify_artists_for_user(user):
            artist = SpotifyArtist.query.filter_by(uri=managed_artist.spotify_artist_uri).one()
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
                        f"<img src='{img_src}'>"
                    ])
                deck.add_note(artist_as_note)
    genanki.Package(deck).write_to_file(filename)


def get_artist_model(user):
    rs_anki_enabled = user.uses_rsAnki_javascript
    api_key = user.api_key

    templates = [
        {
            'name': 'Image>Name',
            'qfmt': get_front(AnkiCard.ARTIST_IMAGE_TO_NAME, api_key, rs_anki_enabled),
            'afmt': get_back(AnkiCard.ARTIST_IMAGE_TO_NAME, rs_anki_enabled),
        },
        {
            'name': 'Name>Image',
            'qfmt': get_front(AnkiCard.ARTIST_NAME_TO_IMAGE, api_key, rs_anki_enabled),
            'afmt': get_back(AnkiCard.ARTIST_NAME_TO_IMAGE, rs_anki_enabled),
        }]

    return genanki.Model(
        SPOTIFY_ARTIST_MODEL_ID,
        'Spotify Artist',
        fields=[
            {'name': 'Artist URI'},
            {'name': 'Name'},
            {'name': 'Image'},
        ],
        css="@import '_anki.css';" if rs_anki_enabled else get_default_css(),
        templates=templates
    )


def get_track_model(user):
    rs_anki_enabled = user.uses_rsAnki_javascript
    api_key = user.api_key
    should_generate_albumart_card = user.username == "rsanek"
    legacy_model_id = 1579060616046

    templates = [
        {
            'name': 'Audio>Artist',
            'qfmt': get_front(AnkiCard.AUDIO_TO_ARTIST, api_key, rs_anki_enabled),
            'afmt': get_back(AnkiCard.AUDIO_TO_ARTIST, rs_anki_enabled),
        }]
    if should_generate_albumart_card:
        templates.append({
            'name': 'Audio+AlbumArt>Artist',
            'qfmt': get_front(AnkiCard.AUDIO_AND_ALBUMART_TO_ARTIST, api_key, rs_anki_enabled),
            'afmt': get_back(AnkiCard.AUDIO_AND_ALBUMART_TO_ARTIST, rs_anki_enabled),
        })
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
        css="@import '_anki.css';" if rs_anki_enabled else get_default_css(),
        templates=templates
    )


def get_back(card_type, rs_anki_enabled):
    script_include = get_rs_anki_custom_script() if rs_anki_enabled else get_default_script()
    if card_type == AnkiCard.AUDIO_TO_ARTIST:
        text_part = """What artist?
<hr>
<ul>
<li><span class="rsAnswer">{{Artist(s)}}</span></li>
<li>{{Track Name}}</li>
<li>{{Album}}</li>
</ul>"""
        image_part = "{{Album Art}}"
    elif card_type == AnkiCard.AUDIO_AND_ALBUMART_TO_ARTIST:
        text_part = """What album?
<hr>
<ul>
<li><span class="rsAnswer">{{Album}}</span></li>
<li>{{Track Name}}</li>
<li>{{Artist(s)}}</li>
</ul>"""
        image_part = "{{Album Art}}"
    elif card_type == AnkiCard.ARTIST_IMAGE_TO_NAME:
        text_part = """<span class="rsAnswer rsAnkiBold">{{Name}}</span>"""
        image_part = "{{Image}}"
    elif card_type == AnkiCard.ARTIST_NAME_TO_IMAGE:
        text_part = """<span class="rsAnkiBold">{{Name}}</span>"""
        image_part = """<span class="rsAnswer">{{Image}}</span>"""
    else:
        raise ValueError('Did not recognize card type.')
    return f"""<div id="textPart">
{text_part}
</div>

<div id="imagePart">{image_part}</div>


{script_include}"""


def get_front(card_type, api_key, rs_anki_enabled):
    extra_include = f"""<script type="text/javascript">
{get_minified_js(api_key)}
</script>"""
    css_class = ""
    if card_type == AnkiCard.AUDIO_TO_ARTIST:
        text_part = """What artist?<br>
<input id="jump" type="submit" onclick="jump()" value="Jump to Random Location"><br><br>
<div id="error" style="color:red"></div>"""
        image_part = ""
    elif card_type == AnkiCard.AUDIO_AND_ALBUMART_TO_ARTIST:
        text_part = """What album?<br>
<input id="jump" type="submit" onclick="jump()" value="Jump to Random Location"><br><br>
<div id="error" style="color:red"></div>"""
        image_part = "{{Album Art}}"
    elif card_type == AnkiCard.ARTIST_IMAGE_TO_NAME:
        text_part = "What artist?"
        image_part = "{{Image}}"
        extra_include = ""
    elif card_type == AnkiCard.ARTIST_NAME_TO_IMAGE:
        text_part = """Visualize <span class="rsAnkiBold">{{Name}}</span>"""
        image_part = """<img src="_blank_person.png">"""
        extra_include = ""
        css_class = "rsAnkiPersonNoteType"
    else:
        raise ValueError('Did not recognize card type.')
    script_include = get_rs_anki_custom_script() if rs_anki_enabled else get_default_script()
    return f"""<div id="textPart">{text_part}
</div>

<div id="imagePart" class="{css_class}">{image_part}</div>


{script_include}
{extra_include}"""


def get_minified_js(api_key):
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
""")


def get_rs_anki_custom_script():
    return """<script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/latest.js?config=TeX-AMS_CHTML"></script>
<script type="text/javascript" src="_jquery-1.11.2.min.js"></script>
<div id="categoryIdentifierFront">{{Tags}}</div>
<script type="text/javascript" src="_AnkiLibrary.js"></script>
<script type="text/javascript">if (typeof rsAnki !== 'undefined') rsAnki.defaultUnified();</script>"""


def get_default_script():
    return """<script type="text/javascript" src="https://code.jquery.com/jquery-1.12.4.min.js"></script>"""


def get_default_css():
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
  font-size: 18px;
}"""
