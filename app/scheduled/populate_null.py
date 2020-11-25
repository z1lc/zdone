import tmdbsimple

from app import kv
from app.themoviedb import backfill_null

if __name__ == "__main__":
    tmdbsimple.API_KEY = kv.get("TMDB_API_KEY")
    backfill_null()
    # populate_null(User.query.filter_by(username="rsanek").one())
