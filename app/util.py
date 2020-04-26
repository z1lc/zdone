from datetime import datetime, timedelta
from typing import Dict, Any

import pytz

JsonDict = Dict[str, Any]

def today():
    return today_datetime().date()


# TODO: split into two methods (3-hour-aware for todos, normal for other usages)
def today_datetime():
    return datetime.now(pytz.timezone('US/Pacific')) - timedelta(hours=3)
