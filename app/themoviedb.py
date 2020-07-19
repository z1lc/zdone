import tmdbsimple

from app import kv, db
from app.models.videos import Video

# https://developers.themoviedb.org/3/configuration/get-api-configuration
BASE_URL = 'https://image.tmdb.org/t/p/'
POSTER_SIZE = 'w500'


# TODO: finish implementing TMDB integration
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
        get_or_add_video(Video(
            id=f"zdone:video:tmdb:{tv['id']}",
            name=tv['name'],
            description=tv['overview'],
            release_date=tv['first_air_date'],
            youtube_trailer_key=get_first_youtube_trailer(tv_details.videos()),
            poster_image_url=get_image_url(tv['poster_path']),
        ))

    for watched, movie in (
            [(True, rtv) for rtv in acct.rated_movies()['results']] +
            [(True, ftv) for ftv in acct.favorite_movies()['results']] +
            [(False, wtv) for wtv in acct.watchlist_movies()['results']]):
        m_id = movie['id']
        title = movie['original_title']
        description = movie['overview']
        image = get_image_url(movie['poster_path'])
        year_released = movie['release_date'][:4]

        movie_detail = tmdbsimple.Movies(m_id)
        # m_info = movie.info()
        # genres = ", ".join([name for _, name in m_info['genres']])

        m_credits = tmdbsimple.Movies(m_id).credits()
        cast = [f"{cast['name']} as {cast['character']}" for cast in m_credits['cast']][:3]
        cast_output = f"<ul>{''.join(['<li>' + as_string + '</li>' for as_string in cast])}</ul>"

        get_or_add_video(Video(
            id=f"zdone:video:tmdb:{m_id}",
            name=title,
            description=description,
            release_date=movie['release_date'],
            youtube_trailer_key=get_first_youtube_trailer(movie_detail.videos()),
            poster_image_url=image,
        ))

        result += "<br>".join([title + f' ({year_released})',
                               description,
                               cast_output,
                               f"<img src='{image}'>",
                               ])

    return result


def get_first_youtube_trailer(videos):
    youtube_trailers = [m for m in videos['results'] if m['site'] == 'YouTube']
    return youtube_trailers[0]['key'] if youtube_trailers else ''


def get_or_add_video(video):
    maybe_persisted_video = Video.query.filter_by(id=video.id).one_or_none()
    if not maybe_persisted_video:
        db.session.add(video)
        db.session.commit()


def get_image_url(path):
    return f"{BASE_URL}{POSTER_SIZE}{path}"
