from datetime import datetime

import pytz

today = datetime.now(pytz.timezone('US/Pacific')).date()
