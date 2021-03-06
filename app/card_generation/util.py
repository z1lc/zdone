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
    loader=PackageLoader("app", "anki_templates"),
    autoescape=select_autoescape(["html", "xml"]),
    undefined=StrictUndefined,
)


# DO NOT CHANGE THESE ENUM NAMES or you will cause backwards incompatibility: the names are used as template names
class AnkiCard(Enum):
    # Spotify Track model
    AUDIO_TO_ARTIST = (1, "spotify_track", "Track URI")
    AUDIO_AND_ALBUM_ART_TO_ALBUM = (2, "spotify_track", "Track URI")  # only used by me, not externally

    # Spotify Artist model
    IMAGE_TO_NAME = (3, "spotify_artist", "Artist URI")
    NAME_TO_IMAGE = (4, "spotify_artist", "Artist URI")
    NAME_AND_IMAGE_TO_SONG = (5, "spotify_artist", "Artist URI")
    SONGS_TO_NAME = (6, "spotify_artist", "Artist URI")
    NAME_AND_IMAGE_TO_GENRES = (7, "spotify_artist", "Artist URI")
    NAME_AND_IMAGE_TO_SIMILAR_ARTISTS = (8, "spotify_artist", "Artist URI")
    NAME_AND_IMAGE_TO_YEARS_ACTIVE = (9, "spotify_artist", "Artist URI")
    EXTRA_ARTIST_TEMPLATE_1 = (10, "spotify_artist", "Artist URI")  # Albums > Name+Image
    EXTRA_ARTIST_TEMPLATE_2 = (11, "spotify_artist", "Artist URI")  # Name+Image > Albums
    EXTRA_ARTIST_TEMPLATE_3 = (12, "spotify_artist", "Artist URI")
    EXTRA_ARTIST_TEMPLATE_4 = (13, "spotify_artist", "Artist URI")
    EXTRA_ARTIST_TEMPLATE_5 = (14, "spotify_artist", "Artist URI")
    EXTRA_ARTIST_TEMPLATE_6 = (15, "spotify_artist", "Artist URI")
    EXTRA_ARTIST_TEMPLATE_7 = (16, "spotify_artist", "Artist URI")
    EXTRA_ARTIST_TEMPLATE_8 = (17, "spotify_artist", "Artist URI")
    EXTRA_ARTIST_TEMPLATE_9 = (18, "spotify_artist", "Artist URI")
    EXTRA_ARTIST_TEMPLATE_10 = (19, "spotify_artist", "Artist URI")

    # Video model
    POSTER_TO_NAME = (20, "video", "zdone Video ID")
    NAME_TO_POSTER = (21, "video", "zdone Video ID")
    VIDEO_TO_NAME = (22, "video", "zdone Video ID")
    DESCRIPTION_TO_NAME = (23, "video", "zdone Video ID")
    NAME_TO_DESCRIPTION = (24, "video", "zdone Video ID")
    NAME_TO_ACTORS = (30, "video", "zdone Video ID")
    NAME_TO_DIRECTOR = (31, "video", "zdone Video ID")
    NAME_TO_CREATOR = (34, "video", "zdone Video ID")

    # Video Person model
    VP_IMAGE_TO_NAME = (25, "video_person", "zdone Person ID", "Image>Name")
    VP_NAME_TO_IMAGE = (26, "video_person", "zdone Person ID", "Name>Image")
    CREDITS_TO_NAME = (27, "video_person", "zdone Person ID")
    NAME_TO_VIDEO_LIST = (28, "video_person", "zdone Person ID")
    NAME_AND_IMAGE_TO_COSTARS = (29, "video_person", "zdone Person ID")

    # Readwise Highlight model
    HIGHLIGHT_CLOZE_1 = (30, "readwise_highlight_cloze", "zdone Highlight ID")

    # Person cards from readwise highlights
    PERSON_IMAGE_TO_NAME = (31, "person", "Name")
    PERSON_KNOWN_FOR_TO_NAME_AND_IMAGE = (32, "person", "Name")
    PERSON_NAME_TO_IMAGE = (33, "person", "Name")

    # Beer via Untappd
    LABEL_TO_NAME = (35, "beer", "zdone Beer ID")
    NAME_TO_BREWERY = (36, "beer", "zdone Beer ID")
    NAME_TO_LABEL = (37, "beer", "zdone Beer ID")
    NAME_TO_STYLE = (38, "beer", "zdone Beer ID")

    def __init__(self, unique_number: int, directory: str, id_field_name: str = None, name_override: str = None):
        self.unique_number = unique_number
        self.directory = directory
        self.id_field_name = id_field_name
        self.name_override = name_override

    def get_raw_template_name(self) -> str:
        return self.name

    def get_pretty_template_name(self) -> str:
        return (
            self.name_override
            if self.name_override
            else self.name.replace("_", " ").title().replace("To", ">").replace("And", "+").replace(" ", "")
        )


class zdNote(genanki.Note):
    @property
    def guid(self):
        return genanki.guid_for(self.fields[0])


# we want to make sure you have actually listened to the artist for a bit, so let's say minimum 3 songs/albums
def create_html_unordered_list(
    input_list: List, min_length: int = 3, max_length: int = 5, should_sort: bool = False
) -> str:
    if len(input_list) < min_length:
        return ""
    if should_sort:
        input_list.sort(key=lambda credit: _sort_credit(credit))
    return f"<ul><li>{'</li><li>'.join(input_list[:max_length])}</li></ul>"


def _sort_credit(credit):
    if " - Present" in credit:
        return -9999
    maybe_year = re.findall("\\d{4}", credit)
    maybe_year.sort()
    if maybe_year:
        return -int(maybe_year[-1])
    else:
        # if we didn't find a date, it's probably because this hasn't been released yet
        return -9998


def get_template(card_type: AnkiCard, user: User) -> JsonDict:
    rs_anki_enabled: bool = user.uses_rsAnki_javascript
    api_key: str = user.api_key
    return {
        "name": card_type.get_pretty_template_name(),
        "qfmt": render_template(card_type, True, api_key, rs_anki_enabled),
        "afmt": render_template(card_type, False, api_key, rs_anki_enabled),
    }


def render_template(card_type: AnkiCard, is_front: bool, api_key: str, rs_anki_enabled: bool) -> str:
    script_include = get_rs_anki_custom_script(is_front) if rs_anki_enabled else get_default_script()

    if is_front and card_type in [AnkiCard.AUDIO_TO_ARTIST, AnkiCard.AUDIO_AND_ALBUM_ART_TO_ALBUM]:
        script_include += f"""<script type="text/javascript">{get_minified_js_for_song_jump(api_key)}</script>"""

    if is_front and card_type in [AnkiCard.VIDEO_TO_NAME]:
        script_include += f"""<script type="text/javascript">{get_minified_js_for_youtube_video()}</script>"""

    # TODO(will/rob) once we have a proper ID field for Person cards, re-introduce logging here.
    if not is_front and card_type.directory != AnkiCard.PERSON_IMAGE_TO_NAME.directory:
        script_include += (
            f"""<script type="text/javascript">{get_minified_js_for_review_log(api_key, card_type)}</script>"""
        )

    try:
        return env.get_template(f"{card_type.directory}/{card_type.name.lower()}.html").render(
            is_front=is_front, script_include=script_include
        )
    except TemplateNotFound as e:
        # don't require us to write blank HTML templates for the extras if we don't want to
        if "extra" in card_type.name.lower():
            return ""
        raise e


# see https://developers.google.com/youtube/iframe_api_reference for docs
def get_minified_js_for_youtube_video() -> str:
    return jsmin(
        """
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
  }"""
    )


def get_minified_js_for_review_log(api_key: str, card_type: AnkiCard) -> str:
    return jsmin(
        f"""
function logReview() {{
  $.getScript("https://www.zdone.co/api/{api_key}/log/{{{{{card_type.id_field_name}}}}}/{card_type.name}");
}};
logReview();
"""
    )


def get_minified_js_for_song_jump(api_key: str) -> str:
    return jsmin(
        f"""
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
"""
    )


def get_rs_anki_custom_script(is_front) -> str:
    return f"""<script type="text/javascript" src="_jquery-1.11.2.min.js"></script>
<div id="categoryIdentifier{"Front" if is_front else "Back"}">{{{{Tags}}}}</div>
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
