import datetime

from app import db
from app.models.base import BaseModel


class ExternalServiceTaskCompletion(BaseModel):
    __tablename__ = "external_service_task_completions"
    id: int = db.Column(db.Integer, primary_key=True)
    user_id: int = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    service: str = db.Column(db.String(128), nullable=False)
    task_id: str = db.Column(db.String(128), nullable=False)
    subtask_id: str = db.Column(db.String(128))
    duration_seconds: int = db.Column(db.Integer)
    at: datetime.datetime = db.Column(db.DateTime)


class Reminder(BaseModel):
    __tablename__ = "reminders"
    id: int = db.Column(db.Integer, primary_key=True)
    user_id: int = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title: str = db.Column(db.Text)
    message: str = db.Column(db.Text)
    active: bool = db.Column(db.Boolean, server_default='true', nullable=False)
    inactive_explanation: str = db.Column(db.Text)


class ReminderNotification(BaseModel):
    __tablename__ = "reminder_notifications"
    id: int = db.Column(db.Integer, primary_key=True)
    reminder_id: int = db.Column(db.Integer, db.ForeignKey('reminders.id'), nullable=False)
    sent_at: datetime.datetime = db.Column(db.DateTime, nullable=False)
    sent_via = db.Column(db.String, nullable=False)


class Task(BaseModel):
    __tablename__ = "tasks"
    id: int = db.Column(db.Integer, primary_key=True)
    user_id: int = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title: str = db.Column(db.Text, nullable=False)
    description: str = db.Column(db.Text, nullable=True)
    ideal_interval: int = db.Column(db.Integer, nullable=False)
    # the local date of last completion, for ease of skew calculation
    last_completion: datetime.date = db.Column(db.Date, nullable=False)
    # local date for when this task can be re-enabled again
    defer_until: datetime.date = db.Column(db.Date, nullable=True)

    def calculate_skew(self, user_local_date: datetime.date) -> float:
        """
        Calculate the overdueness of the task. A value greater than or equal to 1 signifies this task is due.
        Tasks that are currently deferred have a skew of 0.

        :param user_local_date: the local date of the user in their current time zone
        :return: the skew of the task, as a decimal
        """
        if self.defer_until and user_local_date < self.defer_until:
            return 0.0
        return (user_local_date - self.last_completion).days / self.ideal_interval


class TaskLog(BaseModel):
    __tablename__ = "task_logs"
    id: int = db.Column(db.Integer, primary_key=True)
    task_id: int = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    at: datetime.datetime = db.Column(db.DateTime, nullable=False)  # ALWAYS UTC
    # in what time zone were we when we saved the above UTC timestamp?
    at_time_zone: str = db.Column(db.String(128), nullable=False)
    action: str = db.Column(db.Text, nullable=False)