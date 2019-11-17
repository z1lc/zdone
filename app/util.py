from datetime import datetime, timedelta

import pytz


def today():
    return (datetime.now(pytz.timezone('US/Pacific')) - timedelta(hours=3)).date()
