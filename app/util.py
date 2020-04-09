from datetime import datetime, timedelta

import pytz


def today():
    return today_datetime().date()


# TODO: split into two methods (3-hour-aware for todos, normal for other usages)
def today_datetime():
    return datetime.now(pytz.timezone('US/Pacific')) - timedelta(hours=3)
