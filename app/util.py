import datetime
import re
from typing import Dict, Any, Optional, Tuple, Union, List

import pytz
from b2sdk.account_info import InMemoryAccountInfo
from b2sdk.api import B2Api
from flask import jsonify, Response
from pushover import Client

from app import kv, db
from app.models.base import User, GateDef

JsonDict = Dict[str, Any]


def to_tmdb_id(zdone_id: str) -> int:
    return int(zdone_id.split(":")[3])


def htmlize_note(raw_note) -> str:
    for url in set(re.findall(r"(https?://[^\s]+)", raw_note)):
        raw_note = raw_note.replace(url, '<a href="{url}" target="_blank">{url}</a>'.format(url=url))
    return raw_note.replace("\n", "<br>")


def get_navigation(user: User, current_page: str) -> str:
    pages = list()
    if user.trello_api_key and user.trello_api_access_token:
        pages.append('<a href="/" target="_self">Tasks</a>' if current_page != "Tasks" else "Tasks")
    if user.pushover_user_key:
        pages.append(
            '<a href="/reminders" target="_self">Reminders</a>' if current_page != "Reminders" else "Reminders"
        )
    pages.append('<a href="/spotify" target="_self">Music</a>' if current_page != "Music" else "Music")
    if user.tmdb_session_id:
        pages.append('<a href="/video" target="_self">Video</a>' if current_page != "Video" else "Video")
    if user.is_gated(GateDef.SHOW_HACKER_NEWS_LINK):
        pages.append('<a href="/hn" target="_self">HN</a>' if current_page != "HN" else "HN")
    if user.readwise_access_token:
        pages.append(
            '<a href="/highlights" target="_self">Highlights</a>' if current_page != "Highlights" else "Highlights"
        )
    if user.is_gated(GateDef.SHOW_LOGOUT_LINK):
        pages.append('<a href="/logout" target="_self">Log out</a>')
    return " | ".join(pages)


def today() -> datetime.date:
    return today_datetime().date()


def today_datetime() -> datetime.datetime:
    return datetime.datetime.now(pytz.timezone("US/Pacific")) - datetime.timedelta(hours=3)


def validate_api_key(api_key: str) -> Optional[User]:
    return User.query.filter_by(api_key=api_key).one_or_none() if api_key else None


def success() -> Tuple[Response, int]:
    return jsonify({"result": "success"}), 200


def failure(reason: str = "", code: int = 400) -> Tuple[Response, int]:
    return jsonify({"result": "failure", "reason": reason}), code


def api_key_failure() -> Tuple[Response, int]:
    return failure(
        "Make sure you are passing a valid API key in the x-api-key header (POSTs) or within the URL (GETs).", 401
    )


def jsonp(function_name: str, payload: Union[str, Tuple]) -> Response:
    if isinstance(payload, str):
        return Response(f"{function_name}({payload})", mimetype="text/javascript")
    elif isinstance(payload, tuple):
        # we've received payload from a success() or failure() method
        payload = payload[0].get_data().decode("utf-8").replace("\n", "")
        return Response(f"{function_name}({payload})", mimetype="text/javascript")


def get_b2_api():
    info = InMemoryAccountInfo()
    b2_api = B2Api(info)
    b2_api.authorize_account("production", kv.get("B2_KEY_ID"), kv.get("B2_APPLICATION_KEY"))
    return b2_api


def get_pushover_client(user: User):
    return Client(user.pushover_user_key, api_token=kv.get("PUSHOVER_API_TOKEN"))


def get_distinct_users_in_last_week() -> List[str]:
    sql = f"""
with review_logs as (select user_id, at from anki_review_logs),
    song_logs as (select user_id, created_at as at from spotify_plays),
    tasks_logs as (select user_id, at from task_logs),
    hn_logs as (select user_id, at from hn_read_logs),
    reminder_logs as (select user_id, sent_at
                      from reminder_notifications
                               join reminders r on r.id = reminder_notifications.reminder_id),
    all_logs as (select *
                 from review_logs
                 union
                 select *
                 from song_logs
                 union
                 select *
                 from tasks_logs
                 union
                 select *
                 from hn_logs
                 union
                 select *
                 from reminder_logs)
select distinct username, max(id)
from all_logs l
         join users u on u.id = l.user_id
where at >= current_date - interval '7 days' and username <> 'demo'
group by username
order by max(id) asc"""
    return [t[0] for t in list(db.engine.execute(sql))]
