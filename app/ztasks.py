import datetime
from typing import List

from urlextract import URLExtract

from app.util import today

extractor = URLExtract()


class ZDSubTask:
    def __init__(self, id_: str, name: str, completed_date: datetime, note: str, service: str):
        self.id = id_
        self.name = name
        self.completed_date = completed_date
        self.note = htmlize_note(note)
        self.service = service

    def completed_today(self):
        return self.completed_date == today()


class ZDTask:
    def __init__(self,
                 id_: str,
                 name: str,
                 length_minutes: float,
                 due_date: datetime,
                 completed_date: datetime,
                 repeat: str,
                 note: str,
                 service: str,
                 sub_tasks: List[ZDSubTask]):
        self.id = id_
        self.name = name
        self.length_minutes = length_minutes
        self.due_date = due_date
        self.completed_date = completed_date
        self.repeat = repeat
        self.note = htmlize_note(note)
        self.service = service
        self.sub_tasks = sub_tasks

    def get_pie_background_image(self):
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
            [self.id, self.name, str(self.length_minutes), str(self.due_date), str(self.completed_date)]) + "}"

    def completed_today(self):
        return self.completed_date == today()

    def is_repeating(self):
        return self.repeat != ""


def htmlize_note(raw_note):
    for url in set(extractor.find_urls(raw_note)):
        raw_note = raw_note.replace(url, "<a href=\"{url}\" target=\"_blank\">{url}</a>".format(url=url))
    return raw_note.replace("\n", "<br>")
