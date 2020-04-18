import tmdbsimple

from app import kv

# https://developers.themoviedb.org/3/configuration/get-api-configuration
BASE_URL = 'https://image.tmdb.org/t/p/'
POSTER_SIZE = 'w500'


def get_stuff():
    tmdbsimple.API_KEY = kv.get('TMDB_API_KEY')
    acct = tmdbsimple.Account(session_id=kv.get('TMDB_SESSION_ID'))
    acct.info()  # wild that you have to call this to avoid exceptions...

    result = ''

    for movie in acct.rated_movies()['results']:
        m_id = movie['id']
        title = movie['original_title']
        description = movie['overview']
        image = get_image_url(movie['poster_path'])
        year_released = movie['release_date'][:4]

        m_info = tmdbsimple.Movies(m_id).info()
        genres = ", ".join([name for _, name in m_info['genres']])

        m_credits = tmdbsimple.Movies(m_id).credits()
        cast = [f"{cast['name']} as {cast['character']}" for cast in m_credits['cast']][:3]
        cast_output = f"<ul>{''.join(['<li>' + as_string + '</li>' for as_string in cast])}</ul>"

        result += "<br>".join([title + f' ({year_released})', description, cast_output, f"<img src='{image}'>"])

    return result


def get_image_url(path):
    return f"{BASE_URL}{POSTER_SIZE}{path}"
