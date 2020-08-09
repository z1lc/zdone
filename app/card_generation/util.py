import re
from enum import Enum
from time import time
from typing import List

import genanki
from jinja2 import Environment, PackageLoader, select_autoescape, StrictUndefined, TemplateNotFound
from jsmin import jsmin

from app.models.base import User
from app.util import JsonDict

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
    EXTRA_ARTIST_TEMPLATE_1 = (10, 'spotify_artist')  # Albums > Name+Image
    EXTRA_ARTIST_TEMPLATE_2 = (11, 'spotify_artist')  # Name+Image > Albums
    EXTRA_ARTIST_TEMPLATE_3 = (12, 'spotify_artist')
    EXTRA_ARTIST_TEMPLATE_4 = (13, 'spotify_artist')
    EXTRA_ARTIST_TEMPLATE_5 = (14, 'spotify_artist')
    EXTRA_ARTIST_TEMPLATE_6 = (15, 'spotify_artist')
    EXTRA_ARTIST_TEMPLATE_7 = (16, 'spotify_artist')
    EXTRA_ARTIST_TEMPLATE_8 = (17, 'spotify_artist')
    EXTRA_ARTIST_TEMPLATE_9 = (18, 'spotify_artist')
    EXTRA_ARTIST_TEMPLATE_10 = (19, 'spotify_artist')

    # Video model
    POSTER_TO_NAME = (20, 'video')
    NAME_TO_POSTER = (21, 'video')
    VIDEO_TO_NAME = (22, 'video')
    DESCRIPTION_TO_NAME = (23, 'video')
    NAME_TO_DESCRIPTION = (24, 'video')

    # Video Person model
    VP_IMAGE_TO_NAME = (25, 'video_person', 'Image>Name')
    VP_NAME_TO_IMAGE = (26, 'video_person', 'Name>Image')
    CREDITS_TO_NAME = (27, 'video_person')
    NAME_TO_CREDIT = (28, 'video_person')

    def __init__(self, unique_number, directory, name_override=None):
        self.unique_number = unique_number
        self.directory = directory
        self.name_override = name_override

    def get_template_name(self) -> str:
        return self.name_override if self.name_override else self.name \
            .replace('_', ' ') \
            .title() \
            .replace('To', '>') \
            .replace('And', '+') \
            .replace(' ', '')


saved_time = None


def get_card_id() -> int:
    global saved_time
    if not saved_time:
        saved_time = int(time()) * 1000
    else:
        saved_time += 1

    return saved_time


class zdNote(genanki.Note):
    @property
    def guid(self):
        return genanki.guid_for(self.fields[0])

    # copied over exactly except for where noted
    def write_to_db(self, cursor, now_ts, deck_id, note_idx):
        now_ts_milliseconds = now_ts * 1000
        note_id = now_ts_milliseconds + note_idx
        cursor.execute('INSERT INTO notes VALUES(?,?,?,?,?,?,?,?,?,?,?);', (
            note_id,  # id
            self.guid,  # guid
            self.model.model_id,  # mid
            now_ts,  # mod
            -1,  # usn
            self._format_tags(),  # TODO tags
            self._format_fields(),  # flds
            self.sort_field,  # sfld
            0,  # csum, can be ignored
            0,  # flags
            '',  # data
        ))

        for card_idx, card in enumerate(self.cards):
            # this is the only change; there were weird issues with duplicate card_ids getting generated so I just
            # replaced it with a basic counter here.
            card_id = get_card_id()
            card.write_to_db(cursor, now_ts, deck_id, note_id, card_id)


# we want to make sure you have actually listened to the artist for a bit, so let's say minimum 3 songs/albums
def create_html_unordered_list(input_list: List, min_length: int = 3, max_length: int = 5,
                               should_sort: bool = False) -> str:
    if len(input_list) < min_length:
        return ""
    if should_sort:
        input_list.sort(key=lambda credit: _sort_credit(credit))
    return f"<ul><li>{'</li><li>'.join(input_list[:max_length])}</li></ul>"


def _sort_credit(credit):
    maybe_year = re.findall("\d{4}", credit)
    if maybe_year:
        return -int(maybe_year[-1])
    else:
        # if we didn't find a date, it's probably because this hasn't been released yet
        return -9999


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
        script_include += f"""<script type="text/javascript">{get_minified_js_for_song_jump(api_key)}</script>"""

    if is_front and card_type in [AnkiCard.VIDEO_TO_NAME]:
        script_include += f"""<script type="text/javascript">{get_minified_js_for_youtube_video()}</script>"""

    try:
        return env.get_template(f"{card_type.directory}/{card_type.name.lower()}.html") \
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


# see https://developers.google.com/youtube/iframe_api_reference for docs
def get_minified_js_for_youtube_video() -> str:
    return jsmin("""
  var tag = document.createElement('script');

  tag.src = "https://www.youtube.com/iframe_api";
  var firstScriptTag = document.getElementsByTagName('script')[0];
  firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

  var player;
  function onYouTubeIframeAPIReady() {
    player = new YT.Player('player', {
      width: '100%',
      videoId: '{{YouTube Trailer Key}}',
      playerVars: { 'autoplay': 1, 'playsinline': 1, 'start': getRandomInt(10, {{YouTube Trailer Duration}} - 20) },
      events: {
        'onReady': onPlayerReady
      }
    });
  }

  function getRandomInt(min, max) {
    if (max <= min) return min;
    min = Math.ceil(min);
    max = Math.floor(max);
    return Math.floor(Math.random() * (max - min)) + min; //The maximum is exclusive and the minimum is inclusive
  }

  function onPlayerReady(event) {
    event.target.mute();
    event.target.playVideo();
  }""")


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
