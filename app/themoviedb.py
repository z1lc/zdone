import tmdbsimple

from app import kv #, db

# https://developers.themoviedb.org/3/configuration/get-api-configuration
# from app.models.tmdb import Video

BASE_URL = 'https://image.tmdb.org/t/p/'
POSTER_SIZE = 'w500'


# TODO: finish implementing TMDB integration
def get_stuff():
    tmdbsimple.API_KEY = kv.get('TMDB_API_KEY')
    acct = tmdbsimple.Account(session_id=kv.get('TMDB_SESSION_ID'))
    acct.info()  # wild that you have to call this to avoid exceptions...

    result = ''

    for movie in acct.rated_movies()['results'][1:2]:
        m_id = movie['id']
        title = movie['original_title']
        description = movie['overview']
        image = get_image_url(movie['poster_path'])
        year_released = movie['release_date'][:4]

        movie_detail = tmdbsimple.Movies(m_id)
        youtube_trailers = [m for m in movie_detail.videos()['results'] if m['site'] == 'YouTube']
        first_youtube_trailer = ''
        if youtube_trailers:
            first_youtube_trailer = youtube_trailers[0]['key']
        # m_info = movie.info()
        # genres = ", ".join([name for _, name in m_info['genres']])

        m_credits = tmdbsimple.Movies(m_id).credits()
        cast = [f"{cast['name']} as {cast['character']}" for cast in m_credits['cast']][:3]
        cast_output = f"<ul>{''.join(['<li>' + as_string + '</li>' for as_string in cast])}</ul>"

        # get_or_add_video(Video(
        #     id=f"zdone:video:tmdb:{m_id}",
        #     name=title,
        #     description=description,
        #     release_date=movie['release_date'],
        #     youtube_trailer_key=first_youtube_trailer,
        #     poster_image_url=image,
        # ))

        result += "<br>".join([title + f' ({year_released})', description, cast_output, f"<img src='{image}'>",
                               f'<iframe width="560" height="315" src="https://www.youtube.com/embed/{first_youtube_trailer}?controls=0&autoplay=1&mute=1" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>'])

    return result


# def get_or_add_video(video):
#     maybe_persisted_video = Video.query.filter_by(id=video.id).one_or_none()
#     if not maybe_persisted_video:
#         db.session.add(video)
#         db.session.commit()


def get_image_url(path):
    return f"{BASE_URL}{POSTER_SIZE}{path}"
