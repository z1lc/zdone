import datetime
from typing import Optional

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


class Task(BaseModel):
    __tablename__ = "tasks"
    id: int = db.Column(db.Integer, primary_key=True)
    user_id: int = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title: str = db.Column(db.Text, nullable=False)
    description: Optional[str] = db.Column(db.Text, nullable=True)
    ideal_interval: int = db.Column(db.Integer, nullable=False)
    # the local date of last completion, for ease of skew calculation
    last_completion: datetime.date = db.Column(db.Date, nullable=False)
    # local date for when this task can be re-enabled again
    defer_until: Optional[datetime.date] = db.Column(db.Date, nullable=True)

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
        return (user_local_date - self.last_completion).days / self.ideal_interval


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
