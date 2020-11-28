import datetime
from enum import Enum
from typing import Optional

from sentry_sdk import capture_exception

from app import db
from app.models.base import BaseModel


class Reminder(BaseModel):
    __tablename__ = "reminders"
    id: int = db.Column(db.Integer, primary_key=True)
    user_id: int = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title: str = db.Column(db.Text)
    # pushover's limit for the message is 1024 characters https://pushover.net/api
    message: str = db.Column(db.Text)
    active: bool = db.Column(db.Boolean, server_default="true", nullable=False)
    inactive_explanation: str = db.Column(db.Text)


class ReminderNotification(BaseModel):
    __tablename__ = "reminder_notifications"
    id: int = db.Column(db.Integer, primary_key=True)
    reminder_id: int = db.Column(db.Integer, db.ForeignKey("reminders.id"), nullable=False)
    sent_at: datetime.datetime = db.Column(db.DateTime, nullable=False)
    sent_via = db.Column(db.String, nullable=False)


class RecurrenceType(Enum):
    FROM_COMPLETION_DATE = 1
    FROM_DUE_DATE = 2
    NONE = 3


class Task(BaseModel):
    __tablename__ = "tasks"
    id: int = db.Column(db.Integer, primary_key=True)
    user_id: int = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title: str = db.Column(db.Text, nullable=False)
    description: Optional[str] = db.Column(db.Text, nullable=True)
    # Tasks with RecurrenceType.NONE start with an ideal_interval of -1 and switch to 0 once completed
    # All other RecurrenceTypes use positive ideal_intervals
    ideal_interval: int = db.Column(db.Integer, nullable=False)
    # the last_completion column is a bit of a misnomer, as it is not always the date of last completion.
    # It varies based on the recurrence type:
    #   for FROM_COMPLETION_DATE, it is the actual date of last completion.
    #   for FROM_DUE_DATE, it is the date the task *would have* most recently been completed,
    #       if it were completed on time.
    #   for NONE, it is the due date.
    last_completion: datetime.date = db.Column(db.Date, nullable=False)
    # local date for when this task can be re-enabled again
    defer_until: Optional[datetime.date] = db.Column(db.Date, nullable=True)
    recurrence_type: RecurrenceType = db.Column(
        db.Enum(RecurrenceType), nullable=False, server_default=RecurrenceType.FROM_COMPLETION_DATE.name
    )

    def is_after_delay(self, user_local_date: datetime.date) -> bool:
        return self.defer_until is None or user_local_date >= self.defer_until

    def calculate_skew(self, user_local_date: datetime.date, ignore_deferral: bool = False) -> float:
        """
        Calculate the overdueness of the task. A value greater than or equal to 1 signifies this task is due.
        Tasks that are currently deferred have a skew of 0 unless ignore_deferral is passed.

        :param user_local_date: the local date of the user in their current time zone
        :param ignore_deferral: deferred tasks by default have a skew of 0.
                                if passed as true, the true deferral will be calculated
        :return: the skew of the task, as a decimal
        """
        if not ignore_deferral and self.defer_until and user_local_date < self.defer_until:
            return 0.0

        if self.recurrence_type in [RecurrenceType.FROM_COMPLETION_DATE]:
            return (user_local_date - self.last_completion).days / self.ideal_interval
        # we use 100 here & below so that once a specific-date task becomes due,
        # it is always prioritized to the front of the list
        elif self.recurrence_type in [RecurrenceType.FROM_DUE_DATE]:
            return 100 if (user_local_date - self.last_completion).days >= self.ideal_interval else 0
        elif self.recurrence_type in [RecurrenceType.NONE]:
            return 100 if self.ideal_interval == -1 and user_local_date >= self.last_completion else 0
        else:
            capture_exception(ValueError(f"Could not calculate skew for RecurrenceType {self.recurrence_type}"))
            return 0


class TaskLog(BaseModel):
    __tablename__ = "task_logs"
    id: int = db.Column(db.Integer, primary_key=True)
    task_id: Optional[int] = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=True)
    user_id: int = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    task_name: Optional[str] = db.Column(db.Text, nullable=True)
    at: datetime.datetime = db.Column(db.DateTime, nullable=False)  # ALWAYS UTC
    # in what time zone were we when we saved the above UTC timestamp?
    at_time_zone: str = db.Column(db.String(128), nullable=False)
    action: str = db.Column(db.Text, nullable=False)
