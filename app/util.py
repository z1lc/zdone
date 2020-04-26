import datetime
from typing import Dict, Any, Optional

import pytz
from flask import jsonify

from app.models import User

JsonDict = Dict[str, Any]


def today() -> datetime.date:
    return today_datetime().date()


# TODO: split into two methods (3-hour-aware for todos, normal for other usages)
def today_datetime() -> datetime.datetime:
    return datetime.datetime.now(pytz.timezone('US/Pacific')) - datetime.timedelta(hours=3)


def validate_api_key(api_key: str) -> Optional[User]:
    return User.query.filter_by(api_key=api_key).one() if api_key else None


def success():
    return jsonify({
        'result': 'success'
    }), 200


def failure(reason="", code=400):
    return jsonify({
        'result': 'failure',
        'reason': reason
    }), code


def api_key_failure():
    return failure("Make sure you are passing a valid API key in the x-api-key header.", 401)


def jsonp(function_name, payload):
    if isinstance(payload, str):
        return f"{function_name}({payload})"
    elif isinstance(payload, tuple):
        # we've received payload from a success() or failure() method
        payload = payload[0].get_data().decode('utf-8').replace('\n', '')
        return f"{function_name}({payload})"
