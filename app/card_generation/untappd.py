from typing import List

import genanki
from genanki import Deck
from untappd import Untappd

from app import kv
from app.card_generation.util import get_default_css, get_rs_anki_css, get_template, AnkiCard, zdNote
from app.models.base import User
from app.util import JsonDict

BEER_MODEL_ID = 1607000000000


def get_beer_model(user):
    templates: List[JsonDict] = [
        get_template(AnkiCard.LABEL_TO_NAME, user),
        get_template(AnkiCard.NAME_TO_BREWERY, user),
        get_template(AnkiCard.NAME_TO_LABEL, user),
        get_template(AnkiCard.NAME_TO_STYLE, user),
    ]
    return genanki.Model(
        BEER_MODEL_ID,
        "Beer",
        fields=[
            {"name": "zdone Beer ID"},
            {"name": "Name"},
            {"name": "ABV"},
            {"name": "IBU"},
            {"name": "Style"},
            {"name": "Brewery Name"},
            {"name": "Brewery Type"},
            {"name": "Label Image"},
            {"name": "Extra Images"},
            # TODO(rob): Add more fields before public release
        ],
        css=(get_rs_anki_css() if user.uses_rsAnki_javascript else get_default_css()),
        templates=templates,
    )


def generate_beer(user: User, deck: Deck, tags: List[str]):
    client = Untappd(
        client_id=kv.get("UNTAPPD_CLIENT_ID"),
        client_secret=kv.get("UNTAPPD_CLIENT_SECRET"),
        redirect_url="https://www.zdone.co/",
    )
    for beer_response in client.user.beers(user.untappd_username)["response"]["beers"]["items"]:
        beer = client.beer.info(beer_response["beer"]["bid"])["response"]["beer"]
        brewery = beer["brewery"]

        deck.add_note(
            zdNote(
                model=get_beer_model(user),
                tags=tags,
                fields=[
                    f"zdone:beer:untappd:{beer['bid']}",
                    beer["beer_name"],
                    beer["beer_abv"],
                    beer["beer_ibu"],
                    beer["beer_style"],
                    brewery["brewery_name"],
                    # https://www.brewersassociation.org/statistics-and-data/craft-beer-industry-market-segments/
                    # micro = <15k barrels; regional = <6m barrels; macro = >6m
                    brewery["brewery_type"],
                    f"<img src='{beer['beer_label_hd']}'>",
                    "".join([f"<img src='{photo['photo']['photo_img_md']}'>" for photo in beer["media"]["items"][:3]]),
                ],
            )
        )

    print("hi")
