from enum import Enum
from typing import Optional, Tuple, Dict

import isodate
import tmdbsimple
from pyyoutube import Api
from sentry_sdk import capture_exception

from app import kv, db
from app.log import log
from app.models.base import User
from app.models.videos import Video, VideoPerson, VideoCredit, YouTubeVideo, ManagedVideo
# https://developers.themoviedb.org/3/configuration/get-api-configuration
from app.util import today, to_tmdb_id

BASE_URL = 'https://image.tmdb.org/t/p/'
POSTER_SIZE = 'w500'
YOUTUBE_DURATIONS_CACHE: Dict[str, int] = {}


class VideoType(Enum):
    MOVIE = 1
    TV = 2


def _get_full_paginated(function):
    results = list()
    page_number = 1
    total_pages = 10
    while page_number <= total_pages:
        total_pages, this_page_result = _get_page_results(function, page_number)
        if total_pages == 0:
            break
        results.extend(this_page_result)
        page_number += 1
    return results


def _get_page_results(function, page: int):
    ret = function(page=page)
    return ret['total_pages'], ret['results']


def get_stuff(user: User):
    tmdbsimple.API_KEY = kv.get('TMDB_API_KEY')
    # to get session id, GET https://api.themoviedb.org/3/authentication/token/new?api_key=API_KEY
    # then use request_token to forward person to https://www.themoviedb.org/authenticate/REQUEST_TOKEN?redirect_to=http://callback.com
    # then POST to /authentication/session/new with same request_token
    acct = tmdbsimple.Account(session_id=user.tmdb_session_id)
    acct.info()  # wild that you have to call this to avoid exceptions...

    result = ''

    for watched, tv in (
            [(True, rtv) for rtv in _get_full_paginated(acct.rated_tv)] +
            [(True, ftv) for ftv in _get_full_paginated(acct.favorite_tv)] +
            [(False, wtv) for wtv in _get_full_paginated(acct.watchlist_tv)]):
        try:
            video_id = f"zdone:video:tmdb:{tv['id']}"
            get_or_add_tv(video_id, tv, user, watched)
            name_and_year = f"{tv['name']} ({tv['first_air_date'][:4]})"
            log(f"Successfully added {name_and_year}")
            result += f"{name_and_year}<br>"
        except Exception as e:
            log(f"Received exception when trying to add TV show https://www.themoviedb.org/tv/{tv['id']}")
            capture_exception(e)

    for watched, movie in (
            [(True, rm) for rm in _get_full_paginated(acct.rated_movies)] +
            [(True, fm) for fm in _get_full_paginated(acct.favorite_movies)] +
            [(False, wm) for wm in _get_full_paginated(acct.watchlist_movies)]):
        try:
            video_id = f"zdone:video:tmdb:{movie['id']}"
            get_or_add_movie(video_id, movie, user, watched)
            name_and_year = f"{movie['original_title']} ({movie.get('release_date', '9999')[:4]})"
            log(f"Successfully added {name_and_year}")
            result += f"{name_and_year}<br>"
        except Exception as e:
            log(f"Received exception when trying to add movie https://www.themoviedb.org/movie/{movie['id']}")
            capture_exception(e)

    return result


def clean_description(description, video_name, replacement):
    return description \
        .replace(video_name, replacement) \
        .replace(video_name.lower(), replacement)


def hydrate_credits(video_id, credits):
    for credit in credits['cast'] + [c for c in credits['crew'] if c['job'] == 'Director']:
        get_or_add_credit(video_id, credit.get('order', None), credit['credit_id'])
    return


def get_or_add_first_youtube_trailer(videos) -> Optional[str]:
    youtube_trailers = [m for m in videos['results'] if m['site'] == 'YouTube']
    youtube_trailers.sort(key=lambda trailer: _sort_trailer(trailer))
    if youtube_trailers:
        key = youtube_trailers[0]['key']
        if get_or_add_youtube_video(key):
            return key

    return None


# types: https://developers.themoviedb.org/3/movies/get-movie-videos
# Trailer, Teaser, Clip, Featurette, Behind the Scenes, Bloopers
def _sort_trailer(trailer) -> Tuple[int, int]:
    # Trailers are obviously ideal. Clips are also OK. Teasers should really be avoided.
    priorities = ['Trailer', 'Clip', 'Featurette', 'Bloopers', 'Behind the Scenes', 'Teaser']

    duration = _get_video_duration_from_youtube(trailer['key'])
    # if we don't find a duration, it's probably because the video was deleted
    # if the duration is more than 60 minutes, we actually probably have the real movie, which we also don't want
    if not duration or duration > 60 * 60:
        return len(priorities) + 1, 0

    try:
        return priorities.index(trailer['type']), -duration
    except ValueError:
        return len(priorities), -duration


def get_or_add_youtube_video(key: str) -> Optional[YouTubeVideo]:
    maybe_video = YouTubeVideo.query.filter_by(key=key).one_or_none()
    if not maybe_video:
        seconds = _get_video_duration_from_youtube(key)
        if seconds:
            maybe_video = YouTubeVideo(
                key=key,
                duration_seconds=seconds
            )
            db.session.add(maybe_video)
            db.session.commit()
        else:
            return None

    return maybe_video


def _get_video_duration_from_youtube(key) -> Optional[int]:
    if key in YOUTUBE_DURATIONS_CACHE:
        return YOUTUBE_DURATIONS_CACHE.get(key)

    video_data = Api(api_key=kv.get('YOUTUBE_API_KEY')).get_video_by_id(video_id=key)
    # we won't get back metadata from YouTube if the video was deleted, set to private, etc.
    if video_data.items:
        pt_string = video_data.items[0].contentDetails.duration
        seconds = isodate.parse_duration(pt_string).total_seconds()
        YOUTUBE_DURATIONS_CACHE[key] = seconds
        return seconds
    return None


def get_or_add_credit(video_id, order, tmdb_credit_id):
    credit_id = f"zdone:credits:tmdb:{tmdb_credit_id}"
    maybe_credit = VideoCredit.query.filter_by(id=credit_id).one_or_none()
    if not maybe_credit:
        credit_detail = tmdbsimple.Credits(tmdb_credit_id).info()
        person_id = f"zdone:person:tmdb:{credit_detail['person']['id']}"
        get_or_add_person(person_id)
        maybe_credit = VideoCredit(
            id=credit_id,
            video_id=video_id,
            person_id=f"zdone:person:tmdb:{credit_detail['person']['id']}",
            character=credit_detail.get('media').get('character', None),
            job=credit_detail.get('job', None),
            order=order,
        )
        db.session.add(maybe_credit)
        db.session.commit()
    return maybe_credit


def get_or_add_person(person_id: str) -> VideoPerson:
    maybe_person = VideoPerson.query.filter_by(id=person_id).one_or_none()
    if not maybe_person:
        person = tmdbsimple.People(to_tmdb_id(person_id)).info()
        maybe_person = VideoPerson(
            id=person_id,
            name=person['name'],
            image_url=get_full_tmdb_image_url(person['profile_path']),
            birthday=person['birthday'],
            deathday=person['deathday'],
            known_for=person['known_for_department'],
        )
        db.session.add(maybe_person)
        db.session.commit()
    return maybe_person


def get_or_add_movie(movie_id: str, tmdb_api_movie_or_tv_response, user: User, watched: bool) -> Video:
    return get_or_add_video(movie_id, VideoType.MOVIE, tmdb_api_movie_or_tv_response, user, watched)


def get_or_add_tv(tv_id: str, tmdb_api_movie_or_tv_response, user: User, watched: bool) -> Video:
    return get_or_add_video(tv_id, VideoType.TV, tmdb_api_movie_or_tv_response, user, watched)


def get_or_add_video(video_id: str, type: VideoType, tmdb_api_movie_or_tv_response, user: User, watched: bool) -> Video:
    maybe_video = Video.query.filter_by(id=video_id).one_or_none()
    if not maybe_video:
        if type == VideoType.MOVIE:
            m_id = tmdb_api_movie_or_tv_response['id']
            title = tmdb_api_movie_or_tv_response['original_title']
            description = tmdb_api_movie_or_tv_response['overview']
            image = get_full_tmdb_image_url(tmdb_api_movie_or_tv_response['poster_path'])

            movie_detail = tmdbsimple.Movies(m_id)
            info = movie_detail.info()
            maybe_budget = int(info['budget'])
            maybe_revenue = int(info['revenue'])

            m_credits = tmdbsimple.Movies(m_id).credits()
            maybe_video = Video(
                id=video_id,
                name=title,
                description=clean_description(description, title, "[film]"),
                release_date=tmdb_api_movie_or_tv_response.get('release_date', None),
                last_air_date=None,
                youtube_trailer_key=get_or_add_first_youtube_trailer(movie_detail.videos()),
                poster_image_url=image,
                film_or_tv='film',
                budget=maybe_budget if maybe_budget > 0 else None,
                revenue=maybe_revenue if maybe_revenue > 0 else None,
            )
        else:
            tv_details = tmdbsimple.TV(tmdb_api_movie_or_tv_response['id'])
            tv_info = tv_details.info()
            m_credits = tmdbsimple.TV(tmdb_api_movie_or_tv_response['id']).credits()
            maybe_video = Video(
                id=video_id,
                name=tmdb_api_movie_or_tv_response['name'],
                description=clean_description(tmdb_api_movie_or_tv_response['overview'],
                                              tmdb_api_movie_or_tv_response['name'], "[TV show]"),
                release_date=tv_info['first_air_date'],
                last_air_date=tv_info['last_air_date'],
                youtube_trailer_key=get_or_add_first_youtube_trailer(tv_details.videos()),
                poster_image_url=get_full_tmdb_image_url(tmdb_api_movie_or_tv_response['poster_path']),
                film_or_tv='TV show',
            )

        db.session.add(maybe_video)
        db.session.commit()
        hydrate_credits(video_id, m_credits)
        if type == VideoType.TV:
            for i, creator_response in enumerate(tv_info['created_by']):
                get_or_add_credit(video_id, i, creator_response['credit_id'])

    maybe_managed_video = ManagedVideo.query.filter_by(user_id=user.id, video_id=video_id).one_or_none()
    if not maybe_managed_video:
        maybe_managed_video = ManagedVideo(
            user_id=user.id,
            video_id=video_id,
            date_added=today(),
            watched=watched,
        )

        db.session.add(maybe_managed_video)
        db.session.commit()
    else:
        if maybe_managed_video.watched != watched:
            maybe_managed_video.watched = watched
            db.session.commit()

    return maybe_video


def backfill_null():
    for person in VideoPerson.query.all():
        api_person = tmdbsimple.People(to_tmdb_id(person.id)).info()
        person.deathday = api_person['deathday']
        log(f"Added death for {person.name}")
        db.session.commit()
    # for video in Video.query.all():
    #     if video.film_or_tv == "film":
    #         m_videos = tmdbsimple.Movies(to_tmdb_id(video.id)).videos()
    #     else:
    #         m_videos = tmdbsimple.TV(to_tmdb_id(video.id)).videos()
    #     video.youtube_trailer_key = get_or_add_first_youtube_trailer(m_videos)
    #     db.session.commit()


def get_full_tmdb_image_url(path):
    return f"{BASE_URL}{POSTER_SIZE}{path}" if path else None
