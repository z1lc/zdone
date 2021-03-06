from app.models.base import User
from app.util import JsonDict

TEST_USER = User(
    id=1234, username="demo", email="demo@zdone.co", api_key="api-key-demo-1234", uses_rsAnki_javascript=True
)

BECOMING_IMAGE_URL = "https://images-na.ssl-images-amazon.com/images/I/41eRuKxPb3L._SL200_.jpg"


def get_test_highlight(
    id: str = "zdone:highlight:12345",
    text: str = "There are few people whom I really love, and still fewer of whom I think well. The more I see of the "
    "world, the more am I dissatisfied with it; and every day confirms my belief of the inconsistency of "
    "all human characters, and of the little dependence that can be placed on the appearance of merit or "
    "sense.",
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
