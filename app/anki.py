from enum import Enum

import genanki
from jsmin import jsmin

SPOTIFY_TRACK_MODEL_ID = 2145668757
SPOTIFY_TRACK_DECK_ID = 1358352773


class AnkiCard(Enum):
    AUDIO_TO_ARTIST = 1
    AUDIO_AND_ALBUMART_TO_ARTIST = 2


class SpotifyTrackNote(genanki.Note):
    @property
    def guid(self):
        return genanki.guid_for(self.fields[0])


def generate_track_apkg(user, filename):
    deck = genanki.Deck(
        SPOTIFY_TRACK_DECK_ID,
        'Spotify Tracks')
    my_note = SpotifyTrackNote(
        model=get_genanki_model(user.api_key, user.uses_rsAnki_javascript),
        fields=[
            'spotify:track:5HNCy40Ni5BZJFw1TKzRsC',
            'Comfortably Numb TEST',
            'Pink Floyd',
            'The Wall',
            '<img src="https://i.scdn.co/image/ab67616d0000b273288d32d88a616b9a278ddc07">'
        ])
    deck.add_note(my_note)
    genanki.Package(deck).write_to_file(filename)


def get_genanki_model(api_key, rs_anki_enabled):
    return genanki.Model(
        SPOTIFY_TRACK_MODEL_ID,
        'Spotify Track',
        fields=[
            {'name': 'Track URI'},
            {'name': 'Track Name'},
            {'name': 'Artist(s)'},
            {'name': 'Album'},
            {'name': 'Album Art'},
        ],
        css="@import '_anki.css';" if rs_anki_enabled else get_default_css(),
        templates=[
            {
                'name': 'Audio>Artist',
                'qfmt': get_front(AnkiCard.AUDIO_TO_ARTIST, api_key, rs_anki_enabled),
                'afmt': get_back(AnkiCard.AUDIO_TO_ARTIST, rs_anki_enabled),
            },
            {
                'name': 'Audio+AlbumArt>Artist',
                'qfmt': get_front(AnkiCard.AUDIO_AND_ALBUMART_TO_ARTIST, api_key, rs_anki_enabled),
                'afmt': get_back(AnkiCard.AUDIO_AND_ALBUMART_TO_ARTIST, rs_anki_enabled),
            },
        ])


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
    elif card_type == AnkiCard.AUDIO_AND_ALBUMART_TO_ARTIST:
        text_part = """What album?
<hr>
<ul>
<li><span class="rsAnswer">{{Album}}</span></li>
<li>{{Track Name}}</li>
<li>{{Artist(s)}}</li>
</ul>"""
    else:
        raise ValueError('Did not recognize card type.')
    return f"""<div id="textPart">
{text_part}
</div>

<div id="imagePart">{{{{Album Art}}}}</div>


{script_include}"""


def get_front(card_type, api_key, rs_anki_enabled):
    if card_type == AnkiCard.AUDIO_TO_ARTIST:
        text_part = "What artist?"
        image_part = ""
    elif card_type == AnkiCard.AUDIO_AND_ALBUMART_TO_ARTIST:
        text_part = "What album?"
        image_part = "{{Album Art}}"
    else:
        raise ValueError('Did not recognize card type.')
    script_include = get_rs_anki_custom_script() if rs_anki_enabled else get_default_script()
    return f"""<div id="textPart">{text_part}<br>
<input id="jump" type="submit" onclick="jump()" value="Jump to Random Location"><br><br>
<div id="error" style="color:red"></div>
</div>

<div id="imagePart">{image_part}</div>


{script_include}

<script type="text/javascript">
{get_minified_js(api_key)}
</script>"""


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
