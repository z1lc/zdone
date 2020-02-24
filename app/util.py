from datetime import datetime, timedelta

import pytz


def today():
    return today_datetime().date()


def today_datetime():
    return datetime.now(pytz.timezone('US/Pacific')) - timedelta(hours=3)
