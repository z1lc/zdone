from datetime import datetime

import pytz


def today():
    return datetime.now(pytz.timezone('US/Pacific')).date()
