import datetime


class ZDTask:
    def __init__(self, id_: str, name: str, length_minutes: float, due: datetime, completed_today: bool, service: str):
        self.id = id_
        self.name = name
        self.length_minutes = length_minutes
        self.due = due
        self.completed_today = completed_today
        self.service = service

    def __repr__(self):
        return "{" + self.service + "_task" + ", ".join(
            [self.id, self.name, str(self.length_minutes), str(self.due), str(self.completed_today)]) + "}"
