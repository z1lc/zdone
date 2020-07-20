import re
from enum import Enum
from typing import Dict, List, Optional

import genanki
from genanki import Model, Deck
from jinja2 import Environment, PackageLoader, select_autoescape, StrictUndefined, TemplateNotFound
from jsmin import jsmin

from app import db
from app.models.base import User
from app.models.spotify import LegacySpotifyTrackNoteGuidMapping, SpotifyArtist
from app.models.videos import Video
from app.spotify import get_tracks, get_followed_managed_spotify_artists_for_user
from app.util import JsonDict

SPOTIFY_TRACK_MODEL_ID: int = 1586000000000
SPOTIFY_ARTIST_MODEL_ID: int = 1587000000000
VIDEO_MODEL_ID: int = 1588000000000
SPOTIFY_TRACK_DECK_ID: int = 1586000000000

"""
Things to keep in mind when adding new models / templates:
(to avoid "Notes that could not be imported as note type has changed" on Anki import)
 * you can change the qfmt and afmt of a template, as long as the template name stays the same
 * you cannot change the names or total count of templates in a model
 * you cannot change the names or total count of fields in a model

A general, long-term approach to avoiding compatibility problems:
 * Create many more fields than you're going to need at the beginning, naming them something unique.
   You're going to re-purpose these empty fields later for new fields that you'll want to add.
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


class VideoNote(genanki.Note):
    @property
    def guid(self):
        return genanki.guid_for(self.fields[0])


def generate_track_apkg(user: User, filename: str) -> None:
    deck: Deck = Deck(
        SPOTIFY_TRACK_DECK_ID,
        'Spotify Tracks')
    track_model: Model = get_track_model(user)
    artist_model: Model = get_artist_model(user)
    tags: List[str] = [] if user.default_spotify_anki_tag is None else [user.default_spotify_anki_tag]
    legacy_mappings: Dict[str, str] = {lm.spotify_track_uri: lm.anki_guid for lm in
                                       LegacySpotifyTrackNoteGuidMapping.query.filter_by(user_id=user.id).all()}

    for track in get_tracks(user):
        inner_artists = []
        for inner_artist in track['artists']:
            inner_artists.append(inner_artist['name'])
        track_as_note = SpotifyTrackNote(
            model=track_model,
            tags=tags,
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

    top_played_tracks_sql = f"""
select spotify_artist_uri, spotify_track_uri, st.name, count(*) from spotify_tracks st
join spotify_artists sa on st.spotify_artist_uri = sa.uri
join spotify_plays sp on st.uri = sp.spotify_track_uri
where user_id = {user.id}
group by 1, 2, 3
order by 4 desc"""
    top_played_tracks = list(db.engine.execute(top_played_tracks_sql))

    top_played_albums_sql = f"""
select sar.uri, spotify_album_uri, sal.name, released_at, count(*)
from spotify_tracks st
         join spotify_artists sar on st.spotify_artist_uri = sar.uri
         join spotify_plays sp on st.uri = sp.spotify_track_uri
         join spotify_albums sal on sal.uri = st.spotify_album_uri
where user_id = {user.id} and album_type='album'
group by 1, 2, 3, 4
order by 4 desc"""
    top_played_albums = list(db.engine.execute(top_played_albums_sql))

    # artists released internally only so far
    if user.id <= 6:
        for managed_artist in get_followed_managed_spotify_artists_for_user(user, False):
            artist: SpotifyArtist = SpotifyArtist.query.filter_by(uri=managed_artist.spotify_artist_uri).one()

            img_src: Optional[str]
            if artist.good_image and artist.spotify_image_url:
                img_src = artist.spotify_image_url
            elif artist.image_override_name:
                img_src = f"https://www.zdone.co/static/images/artists/{artist.image_override_name}"
            else:
                img_src = None

            top_played_tracks_for_artist = [clean_track_name(row[2]) for row in top_played_tracks if
                                            row[0] == managed_artist.spotify_artist_uri]
            top_played_tracks_for_artist = list(dict.fromkeys(top_played_tracks_for_artist))
            songs = create_html_unordered_list(top_played_tracks_for_artist)

            top_played_albums_for_artist = {clean_album_name(row[2]): row[3].year for row in top_played_albums if
                                            row[0] == managed_artist.spotify_artist_uri}
            albums = create_html_unordered_list(
                [f'<i>{name}</i> ({year})' for name, year in top_played_albums_for_artist.items()])

            genres = ''
            similar_artists = ''
            years_active = ''

            if img_src:
                artist_as_note = SpotifyArtistNote(
                    model=artist_model,
                    tags=tags,
                    fields=[
                        artist.uri,
                        artist.name,
                        f"<img src='{img_src}'>",
                        songs,
                        albums,
                        genres,
                        similar_artists,
                        years_active,
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

    # videos not released yet
    if user.id <= 1:
        video_model = get_video_model(user)
        for video in Video.query.all():
            track_as_note = VideoNote(
                model=video_model,
                tags=tags,
                fields=[
                    video.id,
                    video.film_or_tv,
                    f"<i>{video.name}</i>",
                    video.description,
                    str(video.release_date.year),
                    video.youtube_trailer_key,
                    f"<img src='{video.poster_image_url}'>",
                ])
            deck.add_note(track_as_note)

    genanki.Package(deck).write_to_file(filename)


def clean_album_name(name: str) -> str:
    REGEXES: List[str] = [
        " \\((\\d{4} )?Remaster(ed)?( \\d{4})?\\)$",
        " \\((Super |25th Anniversary )?Deluxe( Edition)?(; Remaster)?\\)$",
        " \\(Bonus Track Version\\)$",
        " \\(The Remaster\\)$",
        " \\(Big Machine Radio Release Special\\)$",
        " \\((Wembley |Expanded )Edition\\)$",
        " \\(Remastered( Version)?\\)$",
        " \\(Radio Edit\\)$",
        " \\(Without Dialogue\\)$",
        " \\((Original Mono & )?Stereo (Mix )?Version(s)?\\)$",
        " \\(Deluxe / Remastered 2015\\)$",
        " \\(With Bonus Selections\\)$",
        " \\(Benny Benassi Presents The Biz\\)",
    ]
    for regex in REGEXES:
        name = re.sub(regex, "", name)
    return name


# we want to make sure you have actually listened to the artist for a bit, so let's say minimum 3 songs
def create_html_unordered_list(input_list: List, min_length: int = 3, max_length: int = 5) -> str:
    if len(input_list) < min_length:
        return ''
    return '<ul><li>' + '</li><li>'.join(input_list[:max_length]) + '</li></ul>'


def clean_track_name(name: str) -> str:
    REGEXES: List[str] = [
        " - (\\d{4} )?Remaster(ed)?( \\d{4})?$",
        " - (Stereo|Original) Mix$",
        " - Bonus Track$",
        " - Radio Edit$",
        " (\\(|\\[)(feat\\.|with).*?(\\)|\\])",
        " - [A-z ]+ Remix",
        " - [A-z ]+ (Radio )?Mix",
        " - (\\d{4}|Stereo|Acoustic|Single) Version",
        " - Panic! At The Disco Version",
        " - With Introduction",
        " \\(Remix\\)",
        " - Remix",
        " - Extended",
        " - From \"[A-z ]+\" Soundtrack",
        " - Featured in [A-z ]+",
        " - Avicii By Avicii",
        " \\(Isak Original Extended\\) - Benny Benassi Presents The Biz",
    ]
    for regex in REGEXES:
        name = re.sub(regex, "", name)
    return name


def get_video_model(user: User) -> Model:
    return genanki.Model(
        VIDEO_MODEL_ID,
        'Video',
        fields=[
            {'name': 'zdone Video ID'},
            {'name': 'Video Type'},
            {'name': 'Name'},
            {'name': 'Description'},
            {'name': 'Year Released'},
            {'name': 'YouTube Trailer Key'},
            {'name': 'Poster Image'},
            # TODO: add extra fields before public release
        ],
        css=(get_rs_anki_css() if user.uses_rsAnki_javascript else get_default_css()) + get_youtube_css(),
        templates=[
            get_template(AnkiCard.POSTER_TO_NAME, user),
            get_template(AnkiCard.NAME_TO_POSTER, user),
            get_template(AnkiCard.VIDEO_TO_NAME, user),
            # TODO: add extra templates before public release
        ]
    )


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
        # the legacy model ID was from when I imported my model to everyone else. I migrated to the publicly-facing,
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
        script_include += f"""<script type="text/javascript">{get_minified_js_for_song_jump(api_key)}</script>"""

    if is_front and card_type in [AnkiCard.VIDEO_TO_NAME]:
        script_include += f"""<script type="text/javascript">{get_minified_js_for_youtube_video()}</script>"""

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
      playerVars: { 'autoplay': 1, 'playsinline': 1, 'start': 10 },
      events: {
        'onReady': onPlayerReady
      }
    });
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


def get_youtube_css() -> str:
    return """
.video-container {
  width: 95vw;
  height: 85vh;
  overflow: hidden;
  position: relative;
}

.video-container iframe {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.video-container iframe {
  pointer-events: none;
  position: absolute;
  top: -60px;
  left: 0;
  width: 100%;
  height: calc(100% + 120px);
}
"""


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
