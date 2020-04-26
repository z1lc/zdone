import datetime
from typing import Dict, Any

import pytz

JsonDict = Dict[str, Any]


def today() -> datetime.date:
    return today_datetime().date()


# TODO: split into two methods (3-hour-aware for todos, normal for other usages)
def today_datetime() -> datetime.datetime:
    return datetime.datetime.now(pytz.timezone('US/Pacific')) - datetime.timedelta(hours=3)
