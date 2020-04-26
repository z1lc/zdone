import datetime
import re
from typing import List, Optional

import dateutil
from dateutil.rrule import rrule
from urlextract import URLExtract

from app.util import today

extractor = URLExtract()


class ZDSubTask:
    def __init__(self,
                 id_: str,
                 name: str,
                 completed_datetime: Optional[datetime.datetime],
                 note: str,
                 service: str):
        self.id = id_
        self.name = name
        self.completed_datetime = completed_datetime
        self.note = htmlize_note(note)
        self.service = service

    def completed_today(self):
        return self.completed_datetime == today()


class ZDTask:
    def __init__(self,
                 id_: str,
                 name: str,
                 length_minutes: float,
                 due_date: Optional[datetime.date],
                 completed_datetime: Optional[datetime.datetime],
                 repeat: str,
                 note: str,
                 service: str,
                 sub_tasks: List[ZDSubTask]):
        self.id = id_
        self.name = name
        self.length_minutes = length_minutes
        self.due_date = due_date
        self.completed_datetime = completed_datetime
        self.repeat = repeat
        self.note = htmlize_note(note)
        self.service = service
        self.sub_tasks = sub_tasks
        self.interval = 0
        self.skew = 0.0

        if self.repeat:
            dummy_start_date = datetime.datetime(2020, 1, 1)
            self.repeat = re.sub(';FROMCOMP', '', self.repeat)
            if 'COUNT' not in self.repeat:
                self.repeat += ';COUNT=2'
            next_dates = list(dateutil.rrule.rrulestr(self.repeat, dtstart=dummy_start_date))
            self.interval = (next_dates[1] - next_dates[0]).days if len(next_dates) > 1 else 0
            # TODO: check logic here (do we really need due_date to do skew calc?)
            if self.due_date:
                compared_to = self.due_date
                if service == "habitica" and self.completed_datetime:
                    compared_to = self.completed_datetime.date() + datetime.timedelta(days=1)
                self.skew = (today() - compared_to).days / self.interval if compared_to <= today() else 0.0

    def get_pie_background_image(self) -> str:
        # https://stackoverflow.com/a/21206274
        if self.length_minutes >= 60:
            return "none"
        elif self.length_minutes > 30:
            return "linear-gradient(" + str(int(90 + (360 * (self.length_minutes - 30) / 60))) + \
                   "deg, transparent 50%, black 50%), linear-gradient(90deg, white 50%, transparent 50%);"
        elif self.length_minutes < 3:
            return "linear-gradient(90deg, transparent 50%, white 50%), linear-gradient(90deg, white 50%, transparent 50%);"
        else:  # 3 <= length_minutes <= 30
            return "linear-gradient(" + str(int(90 + (360 * self.length_minutes / 60))) + \
                   "deg, transparent 50%, white 50%), linear-gradient(90deg, white 50%, transparent 50%);"

    def __repr__(self):
        return "{" + self.service + "_task" + ", ".join(
            [self.id, self.name, str(self.length_minutes), str(self.due_date), str(self.completed_datetime)]) + "}"

    def completed_today(self) -> bool:
        return self.completed_datetime == today()

    def is_repeating(self) -> bool:
        return self.repeat != ""


def htmlize_note(raw_note) -> str:
    for url in set(extractor.find_urls(raw_note)):
        raw_note = raw_note.replace(url, "<a href=\"{url}\" target=\"_blank\">{url}</a>".format(url=url))
    return raw_note.replace("\n", "<br>")
