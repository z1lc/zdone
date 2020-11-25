import datetime
from collections import defaultdict
from typing import List, Dict, Set

import genanki
from dateutil.relativedelta import relativedelta
from genanki import Model, Deck
from sqlalchemy import and_

from app import db
from app.card_generation.util import (
    zdNote,
    create_html_unordered_list,
    AnkiCard,
    get_template,
    get_rs_anki_css,
    get_default_css,
)
from app.log import log
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
    films = get_video_type_ids("film")
    tvs = get_video_type_ids("TV show")
    youtube_overrides = {ytvo.video_id: ytvo.youtube_trailer_key for ytvo in YouTubeVideoOverride.query.all()}
    youtube_durations = {ytv.key: ytv.duration_seconds for ytv in YouTubeVideo.query.all()}
    managed_video_pair = db.session.query(ManagedVideo, Video).join(ManagedVideo).filter_by(user_id=user.id).all()
    watched_uris = [v.id for mv, v in managed_video_pair if mv.watched]

    top_people_sql = f"""
select vp.id
from video_credits vc
         join video_persons vp on vc.person_id = vp.id
         join managed_videos mv on vc.video_id = mv.video_id
         join videos v on vc.video_id = v.id
where ((character is not null and character not like '%%uncredited%%')
    or job = 'Director' or job = 'Creator') and ("order" is null or "order" <= 10) and mv.user_id = {user.id}
group by 1
having sum(case when mv.watched
                    then case when v.seasons is not null
                                  -- cap at 10 seasons per show, and consider 3 seasons as ≈ 1 movie
                                  then least(v.seasons::float, 10.0) / 3
                              else 1 end
                -- 'want to watch' should be counted the same, whether it's a TV show or a movie
                else 0.5 end) >= 4"""
    top_people = [row[0] for row in list(db.engine.execute(top_people_sql))]
    top_people_string = "'" + "','".join(top_people) + "'"

    log("Generating video notes...")
    for managed_video, video in managed_video_pair:
        trailer_key = youtube_overrides.get(video.id, video.youtube_trailer_key) or ""

        release = ""
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

        directors = VideoPerson.query.join(VideoCredit).filter_by(video_id=video.id, job="Director").all()
        creators = VideoPerson.query.join(VideoCredit).filter_by(video_id=video.id, job="Creator").all()

        # seems like order is sometimes 0-based and other times 1-based?
        top_actors = (
            VideoPerson.query.join(VideoCredit)
            .filter_by(video_id=video.id)
            .filter(VideoCredit.order <= 3)  # type: ignore
            .all()[:3]
        )

        top_actors_and_roles = list()
        for vc, vp in (
            db.session.query(VideoCredit, VideoPerson)
            .join(VideoCredit)
            .filter_by(video_id=video.id)
            .filter(VideoCredit.order <= 5)  # type: ignore
            .all()[:5]
        ):
            extra = f" as {vc.character}" if vc.character else ""
            b, sb = ("<b>", "</b>") if vp.id in top_people else ("", "")
            top_actors_and_roles.append((vp.id, f"{b}{vp.name}{sb}{extra}"))
        top_actors_and_roles_html = ""
        if len(set([vpid for vpid, _ in top_actors_and_roles]).intersection(top_people)) > 0:
            top_actors_and_roles_html = create_html_unordered_list(
                [v for _, v in top_actors_and_roles], max_length=99, should_sort=False
            )

        video_as_note = zdNote(
            model=get_video_model(user),
            tags=tags,
            fields=[
                video.id,
                video.film_or_tv,
                f"<i>{video.name}</i>",
                f"<i>{video.original_name}</i>" if video.original_name else "",
                video.description,
                release,
                ", ".join([d.name for d in directors]) if video.is_film() else "",
                ", ".join([c.name for c in creators]) if video.is_tv() else "",
                ", ".join([a.name for a in top_actors]),
                top_actors_and_roles_html,
                "yes" if managed_video.watched else "",
                "yes" if len(set([d.id for d in directors]).intersection(top_people)) > 0 else "",
                "yes" if len(set([c.id for c in creators]).intersection(top_people)) > 0 else "",
                trailer_key,
                str(youtube_durations.get(trailer_key, "")),
                f"<img src='{video.poster_image_url}'>" if video.poster_image_url else "",
                "".join([f"<img src='{d.image_url}'>" for d in directors if d.image_url]) if video.is_film() else "",
                "".join([f"<img src='{c.image_url}'>" for c in creators if c.image_url]) if video.is_tv() else "",
                "".join([f"<img src='{a.image_url}'>" for a in top_actors if a.image_url]),
            ],
        )
        deck.add_note(video_as_note)

    known_for_map = {
        "Acting": "actor",
        "Writing": "writer",
        "Directing": "director",
        "Production": "producer",
    }

    log("Generating video person notes...")
    for video_person in VideoPerson.query.filter(
        and_(VideoPerson.image_url.isnot(None), VideoPerson.id.in_(top_people))  # type: ignore
    ).all():
        has_actor_credit, has_director_credit, has_film_credit, has_tv_credit = False, False, False, False
        credits_with_role, credits_without_role = set(), set()
        for credit in VideoCredit.query.filter_by(person_id=video_person.id).all():
            # based on the above query, we will receive all credits for a top person, even for films that we haven't
            # added at all. Here we add an if statement to make sure that the credit falls into one of our managed
            # videos. There is an option here to consider adding these videos anyway, though -- it would be good to have
            # some awareness of even non-managed videos for a given actor. Perhaps something to tackle in the future.
            if credit.video_id in [v.id for mv, v in managed_video_pair]:
                if credit.video_id in films:
                    has_film_credit = True
                elif credit.video_id in tvs:
                    has_tv_credit = True

                # b and sb represent <b> and </b>, to highlight films we've watched in the unordered list
                b, sb = "", ""
                if credit.video_id in watched_uris:
                    b, sb = "<b>", "</b>"

                video_formatted_name_and_year = video_id_to_html_formatted_name_and_year[credit.video_id]

                if credit.character and "uncredited" not in credit.character:
                    has_actor_credit = True
                    credits_with_role.add(f"{b}{credit.character} in {video_formatted_name_and_year}{sb}")
                    credits_without_role.add(f"{b}{video_formatted_name_and_year}{sb}")
                elif credit.job:
                    has_director_credit = True
                    credits_with_role.add(f"{b}{credit.job} of {video_formatted_name_and_year}{sb}")
                    credits_without_role.add(f"{b}{video_formatted_name_and_year}{sb}")

        co_stars_sql = f"""
with credits as (select * from video_credits where person_id = '{video_person.id}')
select vp.name, v.id
from video_persons vp
         join video_credits vc on vp.id = vc.person_id
         join videos v on vc.video_id = v.id
         full outer join managed_videos mv on v.id = mv.video_id
where v.id in (select credits.video_id from credits) and vp.id in ({top_people_string})
  and vc.person_id != '{video_person.id}' and mv.user_id = {user.id}
  and (job is null or not (job = 'Director' or job = 'Creator'))
group by 1, 2"""
        co_stars = [
            (row[0], video_id_to_html_formatted_name_and_year[row[1]]) for row in list(db.engine.execute(co_stars_sql))
        ]
        co_stars_grouped_by_star = defaultdict(list)
        for star_name, html_formatted_name_and_year in co_stars:
            co_stars_grouped_by_star[star_name].append(html_formatted_name_and_year)
        co_stars_grouped_by_star_list = [
            f'{k} <span class="mini">{", ".join(v)}</span>' for k, v in co_stars_grouped_by_star.items()
        ]

        age = ""
        if not video_person.deathday and video_person.birthday:
            age = str(relativedelta(datetime.date.today(), video_person.birthday).years)

        person_as_note = zdNote(
            model=get_video_person_model(user),
            tags=tags,
            fields=[
                video_person.id,
                video_person.name,
                age,
                known_for_map.get(video_person.known_for, "crew member"),
                create_html_unordered_list(list(credits_with_role), should_sort=True),
                create_html_unordered_list(list(credits_without_role), max_length=99, should_sort=True),
                create_html_unordered_list(co_stars_grouped_by_star_list, max_length=99, should_sort=True),
                f"<img src='{video_person.image_url}'>",
                "Yes" if has_actor_credit else "",
                "Yes" if has_director_credit else "",
                "Yes" if has_film_credit else "",
                "Yes" if has_tv_credit else "",
            ],
        )
        deck.add_note(person_as_note)


def get_video_model(user: User) -> Model:
    return genanki.Model(
        VIDEO_MODEL_ID,
        "Video",
        fields=[
            {"name": "zdone Video ID"},
            {"name": "Video Type"},
            {"name": "Name"},
            {"name": "Original Name"},
            {"name": "Description"},
            {"name": "Year Released"},
            {"name": "Director"},
            {"name": "Creator"},
            {"name": "Top Actors"},
            {"name": "Top Actors and Roles"},
            {"name": "Watched?"},
            {"name": "Create Director Card?"},
            {"name": "Create Creator Card?"},
            {"name": "YouTube Trailer Key"},
            {"name": "YouTube Trailer Duration"},
            {"name": "Poster Image"},
            {"name": "Director Image"},
            {"name": "Creator Image"},
            {"name": "Top Actor Images"},
            # TODO: add extra fields before public release
        ],
        css=(get_rs_anki_css() if user.uses_rsAnki_javascript else get_default_css()) + get_youtube_css(),
        templates=[
            get_template(AnkiCard.POSTER_TO_NAME, user),
            get_template(AnkiCard.NAME_TO_POSTER, user),
            get_template(AnkiCard.VIDEO_TO_NAME, user),
            get_template(AnkiCard.DESCRIPTION_TO_NAME, user),
            get_template(AnkiCard.NAME_TO_DESCRIPTION, user),
            get_template(AnkiCard.NAME_TO_ACTORS, user),
            get_template(AnkiCard.NAME_TO_DIRECTOR, user),
            get_template(AnkiCard.NAME_TO_CREATOR, user),
            # TODO: add extra templates before public release
        ],
    )


def get_video_person_model(user: User) -> Model:
    return genanki.Model(
        VIDEO_PERSON_MODEL_ID,
        "Video Person",
        fields=[
            {"name": "zdone Person ID"},
            {"name": "Name"},
            {"name": "Age"},
            {"name": "Known For"},
            {"name": "Selected Credits"},
            {"name": "Video List"},
            {"name": "Co-stars"},
            {"name": "Image"},
            {"name": "Actor?"},
            {"name": "Director?"},
            {"name": "Has film credit?"},
            {"name": "Has TV credit?"},
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
        ],
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
