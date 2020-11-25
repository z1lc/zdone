import requests
from requests import Response
from sentry_sdk import capture_exception

from app import db
from app.log import log
from app.models.base import User
from app.models.books import ReadwiseBook, ManagedReadwiseBook, ReadwiseHighlight
from app.util import JsonDict

READWISE_BASE_URL = "https://readwise.io/api/v2"


def upsert_book(user: User, book: JsonDict):
    id = f'zdone:book:readwise:{book["id"]}'
    maybe_book = ReadwiseBook.query.filter_by(id=id).one_or_none()
    if not maybe_book:
        maybe_book = ReadwiseBook()
        db.session.add(maybe_book)
    maybe_book.id = id
    maybe_book.title = book["title"]
    maybe_book.author = book["author"]
    maybe_book.cover_image_url = book["cover_image_url"]
    db.session.commit()

    maybe_managed_book = ManagedReadwiseBook.query.filter_by(readwise_book_id=id, user_id=user.id).one_or_none()
    if not maybe_managed_book:
        maybe_managed_book = ManagedReadwiseBook()
        db.session.add(maybe_managed_book)
    maybe_managed_book.readwise_book_id = id
    maybe_managed_book.user_id = user.id
    maybe_managed_book.category = book["category"]
    db.session.commit()


def upsert_highlight(user: User, highlight: JsonDict):
    id = f'zdone:highlight:readwise:{highlight["id"]}'
    corresponding_managed_book_id = (
        ManagedReadwiseBook.query.filter_by(
            readwise_book_id=f'zdone:book:readwise:{highlight["book_id"]}', user_id=user.id
        )
        .one()
        .id
    )

    maybe_highlight = ReadwiseHighlight.query.filter_by(id=id).one_or_none()
    if not maybe_highlight:
        maybe_highlight = ReadwiseHighlight()
        db.session.add(maybe_highlight)
    maybe_highlight.id = id
    maybe_highlight.managed_readwise_book_id = corresponding_managed_book_id
    maybe_highlight.text = highlight["text"]
    try:
        db.session.commit()
    except Exception as e:
        # If the exception is because of the unique constraint, it's fine, just rollback + skip.
        # If it's not, though, we'd like to know.
        if "_managed_readwise_book_id_and_text" in repr(e):
            log(
                f'Highlight with text "{highlight["text"]}" appears to already be in the database for'
                f" managed_readwise_book_id {corresponding_managed_book_id}. Will skip inserting duplicate."
            )
            db.session.rollback()
        else:
            capture_exception(e)


def get(user: User, endpoint: str, page: int = 1) -> Response:
    tries = 0
    saved_exception = None
    headers = {"Authorization": f"Token {user.readwise_access_token}"}
    query_string = {"page_size": 1000, "page": page}

    while tries < 10:
        tries += 1
        try:
            return requests.get(url=f"{READWISE_BASE_URL}/{endpoint}/", headers=headers, params=query_string)
        except Exception as e:
            saved_exception = e
            continue
    if saved_exception:
        capture_exception(saved_exception)
    return Response()


def get_paginated(user: User, endpoint: str):
    done = False
    page = 1
    results = []
    while not done:
        returned = get(user, endpoint, page).json()
        results.extend(returned["results"])
        page += 1
        done = returned["next"] is None
    log(f"Got {len(results)} results for user {user.username} on Readwise endpoint {endpoint}.")
    return results


def refresh_highlights_and_books(user: User) -> None:
    if get(user, "auth").status_code != 204:
        error = (
            f"Error! Received non-204 response during access token validation from Readwise for user {user.username}"
        )
        log(error)
        capture_exception(ValueError(error))
        return

    log(f"Refreshing all books...")
    for book in get_paginated(user, "books"):
        upsert_book(user, book)

    log(f"Refreshing all highlights...")
    for highlight in get_paginated(user, "highlights"):
        upsert_highlight(user, highlight)
