import re
from typing import Dict, List, Optional

import genanki
from genanki import Model, Deck

from app import db
from app.card_generation.util import create_html_unordered_list, zdNote, get_template, AnkiCard, get_default_css, \
    get_rs_anki_css
from app.models.base import User
from app.models.spotify import LegacySpotifyTrackNoteGuidMapping
from app.spotify import get_tracks, get_common_artists
from app.util import JsonDict

SPOTIFY_TRACK_MODEL_ID: int = 1586000000000
SPOTIFY_ARTIST_MODEL_ID: int = 1587000000000


class SpotifyTrackNote(zdNote):
    # this more-extended version of guid methods is necessary to provide the legacy guid behavior
    @property
    def guid(self):
        if self._guid is None:
            return genanki.guid_for(self.fields[0])
        return self._guid

    @guid.setter
    def guid(self, val):
        self._guid = val


def generate_tracks(user: User, deck: Deck, tags: List[str]):
    legacy_mappings: Dict[str, str] = {lm.spotify_track_uri: lm.anki_guid for lm in
                                       LegacySpotifyTrackNoteGuidMapping.query.filter_by(user_id=user.id).all()}
    for track in get_tracks(user):
        inner_artists = []
        for inner_artist in track['artists']:
            inner_artists.append(inner_artist['name'])
        track_as_note = SpotifyTrackNote(
            model=get_track_model(user),
            tags=tags,
            fields=[
                track['uri'],
                track['name'].replace('"', '\''),
                ", ".join(inner_artists).replace('"', '\''),
                track['album']['name'].replace('"', '\''),
                f"<img src='{track['album']['images'][0]['url']}'>"
            ])
        if track['uri'] in legacy_mappings:
            track_as_note.guid = legacy_mappings.get(track['uri'])
        deck.add_note(track_as_note)


def generate_artists(user: User, deck: Deck, tags: List[str]):
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
    for artist in get_common_artists(user):
        img_src: Optional[str]
        if artist.good_image and artist.spotify_image_url:
            img_src = artist.spotify_image_url
        elif artist.image_override_name:
            img_src = f"https://www.zdone.co/static/images/artists/{artist.image_override_name}"
        else:
            img_src = None

        top_played_tracks_for_artist = [clean_track_name(row[2]) for row in top_played_tracks if row[0] == artist.uri]
        top_played_tracks_for_artist = list(dict.fromkeys(top_played_tracks_for_artist))
        songs = create_html_unordered_list(top_played_tracks_for_artist)

        top_played_albums_for_artist = {clean_album_name(row[2]): row[3].year for row in top_played_albums if
                                        row[0] == artist.uri}
        albums = create_html_unordered_list(
            [f'<i>{name}</i> ({year})' for name, year in top_played_albums_for_artist.items()], max_length=10)

        top_collaborators = list()
        if user.id == 1:
            top_collaborators_sql = f"""
with tracks_by_artist_with_plays as (select sp.spotify_track_uri
                                     from spotify_plays sp
                                              join spotify_features sf on sp.spotify_track_uri = sf.spotify_track_uri
                                     where sf.spotify_artist_uri = '{artist.uri}' and
                                         user_id = {user.id}),
    plays_per_song as (select st.uri, count(*) as plays_for_song
                       from spotify_tracks st
                                join tracks_by_artist_with_plays tbawp on st.uri = tbawp.spotify_track_uri
                       group by 1)
select sa.name, sum(plays_for_song)
from spotify_features sf
         join plays_per_song pps on pps.uri = sf.spotify_track_uri
         join spotify_artists sa on sf.spotify_artist_uri = sa.uri
group by 1
order by sum(plays_for_song) desc"""
            top_collaborators = [row[0] for row in list(db.engine.execute(top_collaborators_sql))]
            top_collaborators.remove(artist.name)

        genres = ''
        similar_artists = ''
        years_active = ''

        if img_src:
            artist_as_note = zdNote(
                model=get_artist_model(user),
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
                    create_html_unordered_list(top_collaborators, max_length=10),
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
            {'name': 'Extra Field 1'},  # Collaborators / featured artists
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
        " \\((Unmixed|The) Extended (Mixes|Versions)\\)",
    ]
    for regex in REGEXES:
        name = re.sub(regex, "", name)
    return name


def clean_track_name(name: str) -> str:
    REGEXES: List[str] = [
        " - (\\d{4} )?(r|R)emaster(ed)?( \\d{4})?$",
        " - (Stereo|Original)( Mix)?$",
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
        " - Album Version / Stereo",
        " - Live At The Lyceum, London/1975",
        " - Edit",
        " - Live at Folsom State Prison, Folsom, CA - January 1968",
    ]
    for regex in REGEXES:
        name = re.sub(regex, "", name)
    return name
