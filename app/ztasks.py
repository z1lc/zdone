import datetime


class ZDTask:
    def __init__(self, id_: str, name: str, length_minutes: float, due: datetime, completed_today: bool, service: str):
        self.id = id_
        self.name = name
        self.length_minutes = length_minutes
        self.due = due
        self.completed_today = completed_today
        self.service = service

        # https://stackoverflow.com/a/21206274
        if length_minutes >= 60:
            self.pie_background_image = "none"
        elif length_minutes > 30:
            self.pie_background_image = "linear-gradient(" + str(int(90 + (360 * (length_minutes - 30) / 60))) + \
                                        "deg, transparent 50%, black 50%), linear-gradient(90deg, white 50%, transparent 50%);"
        elif length_minutes < 3:
            self.pie_background_image = "linear-gradient(90deg, transparent 50%, white 50%), linear-gradient(90deg, white 50%, transparent 50%);"
        else:  # 3 <= length_minutes <= 30
            self.pie_background_image = "linear-gradient(" + str(int(90 + (360 * length_minutes / 60))) + \
                                        "deg, transparent 50%, white 50%), linear-gradient(90deg, white 50%, transparent 50%);"

    def __repr__(self):
        return "{" + self.service + "_task" + ", ".join(
            [self.id, self.name, str(self.length_minutes), str(self.due), str(self.completed_today)]) + "}"
