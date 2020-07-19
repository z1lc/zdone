import tmdbsimple

from app import kv, db
from app.models.videos import Video, VideoPerson, VideoCredit

# https://developers.themoviedb.org/3/configuration/get-api-configuration
BASE_URL = 'https://image.tmdb.org/t/p/'
POSTER_SIZE = 'w500'


def get_stuff():
    tmdbsimple.API_KEY = kv.get('TMDB_API_KEY')
    acct = tmdbsimple.Account(session_id=kv.get('TMDB_SESSION_ID'))
    acct.info()  # wild that you have to call this to avoid exceptions...

    result = ''

    for watched, tv in (
            [(True, rtv) for rtv in acct.rated_tv()['results']] +
            [(True, ftv) for ftv in acct.favorite_tv()['results']] +
            [(False, wtv) for wtv in acct.watchlist_tv()['results']]):
        tv_details = tmdbsimple.TV(tv['id'])
        m_credits = tmdbsimple.TV(tv['id']).credits()
        video_id = f"zdone:video:tmdb:{tv['id']}"
        hydrate_credits(video_id, m_credits)

        get_or_add_video(Video(
            id=video_id,
            name=tv['name'],
            description=tv['overview'],
            release_date=tv['first_air_date'],
            youtube_trailer_key=get_first_youtube_trailer(tv_details.videos()),
            poster_image_url=get_full_tmdb_image_url(tv['poster_path']),
            film_or_tv='TV show',
        ))

    for watched, movie in (
            [(True, rtv) for rtv in acct.rated_movies()['results']] +
            [(True, ftv) for ftv in acct.favorite_movies()['results']] +
            [(False, wtv) for wtv in acct.watchlist_movies()['results']]):
        m_id = movie['id']
        title = movie['original_title']
        description = movie['overview']
        image = get_full_tmdb_image_url(movie['poster_path'])
        year_released = movie['release_date'][:4]

        movie_detail = tmdbsimple.Movies(m_id)
        # m_info = movie.info()
        # genres = ", ".join([name for _, name in m_info['genres']])

        m_credits = tmdbsimple.Movies(m_id).credits()
        video_id = f"zdone:video:tmdb:{m_id}"
        hydrate_credits(video_id, m_credits)

        get_or_add_video(Video(
            id=video_id,
            name=title,
            description=description,
            release_date=movie['release_date'],
            youtube_trailer_key=get_first_youtube_trailer(movie_detail.videos()),
            poster_image_url=image,
            film_or_tv='film',
        ))

        result += title + f' ({year_released})<br>'

    return result


def hydrate_credits(video_id, credits):
    for credit in credits['cast']:
        get_or_add_credit(video_id, credit)
    return


def get_first_youtube_trailer(videos):
    youtube_trailers = [m for m in videos['results'] if m['site'] == 'YouTube']
    return youtube_trailers[0]['key'] if youtube_trailers else ''


def get_or_add_credit(video_id, credit):
    credit_id = f"zdone:credits:tmdb:{credit['credit_id']}"
    maybe_credit = VideoCredit.query.filter_by(id=credit_id).one_or_none()
    if not maybe_credit:
        credit_detail = tmdbsimple.Credits(credit['credit_id']).info()
        person_id = f"zdone:person:tmdb:{credit_detail['person']['id']}"
        get_or_add_person(person_id)
        maybe_credit = VideoCredit(
            id=credit_id,
            video_id=video_id,
            person_id=f"zdone:person:tmdb:{credit_detail['person']['id']}",
            character=credit['character'],
            order=credit['order'],
        )
        db.session.add(maybe_credit)
        db.session.commit()
    return maybe_credit


def get_or_add_person(person_id):
    maybe_person = VideoPerson.query.filter_by(id=person_id).one_or_none()
    if not maybe_person:
        person = tmdbsimple.People(int(person_id.split(":")[3])).info()
        maybe_person = VideoPerson(
            id=person_id,
            name=person['name'],
            image_url=get_full_tmdb_image_url(person['profile_path']),
            birthday=person['birthday'],
            known_for=person['known_for_department'],
        )
        db.session.add(maybe_person)
        db.session.commit()
    return maybe_person


def get_or_add_video(video):
    if not Video.query.filter_by(id=video.id).one_or_none():
        db.session.add(video)
        db.session.commit()


def get_full_tmdb_image_url(path):
    return f"{BASE_URL}{POSTER_SIZE}{path}" if path else None
