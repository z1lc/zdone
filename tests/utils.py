from app.models.base import User
from app.util import JsonDict

TEST_USER = User(
    id=1, username="rsanek", email="rsanek@gmail.com", api_key="api-key-rsanek-1234", uses_rsAnki_javascript=True
)

BECOMING_IMAGE_URL = "https://images-na.ssl-images-amazon.com/images/I/41eRuKxPb3L._SL200_.jpg"


def get_test_highlight(
    id: str = "zdone:highlight:12345",
    text: str = "It is a truth universally acknowledged, that a single man in possession of a good fortune, "
    "must be in want of a wife.",
    source_title: str = "Pride and Prejudice",
    source_author: str = "Jane Austen",
    cover_image_url: str = BECOMING_IMAGE_URL,
) -> JsonDict:
    return {
        "id": id,
        "text": text,
        "source_title": source_title,
        "source_author": source_author,
        "cover_image_url": cover_image_url,
    }
