from collections import defaultdict
from typing import List, Dict, Set

import genanki
from genanki import Model, Deck

from app import db
from app.card_generation.util import zdNote, create_html_unordered_list, AnkiCard, get_template, get_rs_anki_css, \
    get_default_css
from app.models.base import User
from app.models.videos import Video, YouTubeVideoOverride, YouTubeVideo, VideoPerson, VideoCredit, ManagedVideo

VIDEO_MODEL_ID: int = 1588000000000
VIDEO_PERSON_MODEL_ID: int = 1589000000000


def get_video_type_ids(type: str) -> Set[str]:
    sql = f"""
select id
from videos
where film_or_tv='{type}'"""
    return set([row[0] for row in list(db.engine.execute(sql))])


def generate_videos(user: User, deck: Deck, tags: List[str]):
    video_id_to_html_formatted_name_and_year: Dict[str, str] = {}
    films = get_video_type_ids('film')
    tvs = get_video_type_ids('TV show')
    youtube_overrides = {ytvo.video_id: ytvo.youtube_trailer_key for ytvo in YouTubeVideoOverride.query.all()}
    youtube_durations = {ytv.key: ytv.duration_seconds for ytv in YouTubeVideo.query.all()}
    managed_video_pair = db.session.query(ManagedVideo, Video) \
        .join(ManagedVideo) \
        .filter_by(user_id=user.id) \
        .all()
    for managed_video, video in managed_video_pair:
        trailer_key = youtube_overrides.get(video.id, video.youtube_trailer_key) or ''

        release = ''
        if video.release_date:
            release = str(video.release_date.year)
            if video.in_production:
                release += f" - Present"
            elif video.last_air_date:
                if video.last_air_date and video.release_date.year != video.last_air_date.year:
                    release += f" - {str(video.last_air_date.year)}"
            video_id_to_html_formatted_name_and_year[video.id] = f"<i>{video.name}</i> ({release})"
        else:
            video_id_to_html_formatted_name_and_year[video.id] = f"<i>{video.name}</i>"

        directors = VideoPerson.query.join(VideoCredit).filter_by(video_id=video.id, job='Director').all()

        video_as_note = zdNote(
            model=get_video_model(user),
            tags=tags,
            fields=[
                video.id,
                video.film_or_tv,
                f"<i>{video.name}</i>",
                video.description,
                release,
                ", ".join([d.name for d in directors]) if video.is_film() else '',
                'yes' if managed_video.watched else '',
                trailer_key,
                str(youtube_durations.get(trailer_key, '')),
                f"<img src='{video.poster_image_url}'>",
            ])
        deck.add_note(video_as_note)

    top_people_sql = """
select vp.id
from video_credits vc
         join video_persons vp on vc.person_id = vp.id
         join managed_videos mv on vc.video_id = mv.video_id
where ((character is not null and character not like '%%uncredited%%')
    or job = 'Director') and ("order" is null or "order" <= 10)
group by 1
having sum(case when mv.watched then 1 else 0.5 end) >= 4"""
    top_people = [row[0] for row in list(db.engine.execute(top_people_sql))]
    top_people_string = "'" + "','".join(top_people) + "'"

    known_for_map = {
        "Acting": "actor",
        "Writing": "writer",
        "Directing": "director",
        "Production": "producer",
    }

    for video_person in VideoPerson.query.filter(VideoPerson.id.in_(top_people)).all():  # type: ignore
        has_actor_credit = False
        has_director_credit = False
        has_film_credit = False
        has_tv_credit = False
        credits_with_role = set()
        credits_without_role = set()
        for credit in VideoCredit.query.filter_by(person_id=video_person.id).all():
            if credit.video_id in films:
                has_film_credit = True
            elif credit.video_id in tvs:
                has_tv_credit = True

            if credit.character and "uncredited" not in credit.character:
                has_actor_credit = True
                credits_with_role.add(
                    f"{credit.character} in {video_id_to_html_formatted_name_and_year[credit.video_id]}")
                credits_without_role.add(video_id_to_html_formatted_name_and_year[credit.video_id])
            elif credit.job:
                has_director_credit = True
                credits_with_role.add(f"{credit.job} of {video_id_to_html_formatted_name_and_year[credit.video_id]}")
                credits_without_role.add(video_id_to_html_formatted_name_and_year[credit.video_id])

        co_stars_sql = f"""
with credits as (select * from video_credits where person_id = '{video_person.id}')
select vp.name, v.id
from video_persons vp
         join video_credits vc on vp.id = vc.person_id
         join videos v on vc.video_id = v.id
         full outer join managed_videos mv on v.id = mv.video_id
where v.id in (select credits.video_id from credits) and vp.id in ({top_people_string})
  and vc.person_id != '{video_person.id}'
group by 1, 2"""
        co_stars = [(row[0], video_id_to_html_formatted_name_and_year[row[1]]) for row in
                    list(db.engine.execute(co_stars_sql))]
        co_stars_grouped_by_star = defaultdict(list)
        for k, v in co_stars:
            co_stars_grouped_by_star[k].append(v)
        co_stars_grouped_by_star_list = [f'{k} <span class="mini">{", ".join(v)}</span>' for k, v in
                                         co_stars_grouped_by_star.items()]

        person_as_note = zdNote(
            model=get_video_person_model(user),
            tags=tags,
            fields=[
                video_person.id,
                video_person.name,
                known_for_map.get(video_person.known_for, "crew member"),
                create_html_unordered_list(list(credits_with_role), should_sort=True),
                create_html_unordered_list(list(credits_without_role), max_length=99, should_sort=True),
                create_html_unordered_list(co_stars_grouped_by_star_list, max_length=99, should_sort=True),
                f"<img src='{video_person.image_url}'>",
                'Yes' if has_actor_credit else '',
                'Yes' if has_director_credit else '',
                'Yes' if has_film_credit else '',
                'Yes' if has_tv_credit else '',
            ])
        deck.add_note(person_as_note)


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
            {'name': 'Director'},
            {'name': 'Watched?'},
            {'name': 'YouTube Trailer Key'},
            {'name': 'YouTube Trailer Duration'},
            {'name': 'Poster Image'},
            # TODO: add extra fields before public release
        ],
        css=(get_rs_anki_css() if user.uses_rsAnki_javascript else get_default_css()) + get_youtube_css(),
        templates=[
            get_template(AnkiCard.POSTER_TO_NAME, user),
            get_template(AnkiCard.NAME_TO_POSTER, user),
            get_template(AnkiCard.VIDEO_TO_NAME, user),
            get_template(AnkiCard.DESCRIPTION_TO_NAME, user),
            get_template(AnkiCard.NAME_TO_DESCRIPTION, user),
            # TODO: add extra templates before public release
        ]
    )


def get_video_person_model(user: User) -> Model:
    return genanki.Model(
        VIDEO_PERSON_MODEL_ID,
        'Video Person',
        fields=[
            {'name': 'zdone Person ID'},
            {'name': 'Name'},
            {'name': 'Known For'},
            {'name': 'Selected Credits'},
            {'name': 'Video List'},
            {'name': 'Co-stars'},
            {'name': 'Image'},
            {'name': 'Actor?'},
            {'name': 'Director?'},
            {'name': 'Has film credit?'},
            {'name': 'Has TV credit?'},
            # TODO: add extra fields before public release
        ],
        css=(get_rs_anki_css() if user.uses_rsAnki_javascript else get_default_css()) + get_youtube_css(),
        templates=[
            get_template(AnkiCard.VP_IMAGE_TO_NAME, user),
            get_template(AnkiCard.VP_NAME_TO_IMAGE, user),
            get_template(AnkiCard.CREDITS_TO_NAME, user),
            get_template(AnkiCard.NAME_TO_VIDEO_LIST, user),
            get_template(AnkiCard.NAME_AND_IMAGE_TO_COSTARS, user),
            # TODO: add extra templates before public release
        ]
    )


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
