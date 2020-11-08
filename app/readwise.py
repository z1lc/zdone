import requests
from sentry_sdk import capture_exception

from log import log
from models.base import User


def refresh_highlights_and_books(user: User):
    response = requests.get(
        url="https://readwise.io/api/v2/auth/",
        headers={"Authorization": f"Token {user.readwise_access_token}"},
    )
    if response.status_code != 204:
        error = f'Error! Received non-204 response during access token validation from Readwise for user {user.username}'
        log(error)
        capture_exception(ValueError(error))
