import datetime
from typing import Dict, Any, Optional, Tuple, Union

import pytz
from flask import jsonify, Response
from urlextract import URLExtract

from app.models.base import User

JsonDict = Dict[str, Any]

extractor = URLExtract()


def htmlize_note(raw_note) -> str:
    for url in set(extractor.find_urls(raw_note)):
        raw_note = raw_note.replace(url, "<a href=\"{url}\" target=\"_blank\">{url}</a>".format(url=url))
    return raw_note.replace("\n", "<br>")


def get_navigation(user: User, current_page: str) -> str:
    pages = list()
    pages.append('<a href="/spotify" target="_self">Music</a>' if current_page != "Music" else "Music")
    # TODO: replace with user.tmdb_session_key when release
    if user.id == 1:
        pages.append('<a href="/video" target="_self">Video</a>' if current_page != "Video" else "Video")
    if user.pushover_user_key:
        pages.append(
            '<a href="/reminders" target="_self">Reminders</a>' if current_page != "Reminders" else "Reminders")
    if user.trello_api_key and user.trello_api_access_token:
        pages.append('<a href="/" target="_self">Tasks</a>' if current_page != "Tasks" else "Tasks")
    return " | ".join(pages)


def today() -> datetime.date:
    return today_datetime().date()


# TODO: split into two methods (3-hour-aware for todos, normal for other usages)
def today_datetime() -> datetime.datetime:
    return datetime.datetime.now(pytz.timezone('US/Pacific')) - datetime.timedelta(hours=3)


def validate_api_key(api_key: str) -> Optional[User]:
    return User.query.filter_by(api_key=api_key).one() if api_key else None


def success() -> Tuple[Response, int]:
    return jsonify({
        'result': 'success'
    }), 200


def failure(reason: str = "", code: int = 400) -> Tuple[Response, int]:
    return jsonify({
        'result': 'failure',
        'reason': reason
    }), code


def api_key_failure() -> Tuple[Response, int]:
    return failure("Make sure you are passing a valid API key in the x-api-key header.", 401)


def jsonp(function_name: str, payload: Union[str, Tuple]) -> str:
    if isinstance(payload, str):
        return f"{function_name}({payload})"
    elif isinstance(payload, tuple):
        # we've received payload from a success() or failure() method
        payload = payload[0].get_data().decode('utf-8').replace('\n', '')
        return f"{function_name}({payload})"
