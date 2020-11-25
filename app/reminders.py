import datetime
import statistics
from typing import List, Optional

import pytz
from pushover import Client

from app import kv, db
from app.log import log
from app.models.base import User
from app.models.tasks import Reminder, ReminderNotification, TaskLog, Task
from app.util import today, get_pushover_client


def get_reminders(user: User) -> List[Reminder]:
    return Reminder.query.filter_by(user_id=user.id).all()


def get_unseen_reminders(user: User) -> List[Reminder]:
    unseen_ids = f"""
select r.id
from reminders r
         left join reminder_notifications rn on r.id = rn.reminder_id
where rn.id is null and user_id={user.id} and active"""
    unseen_list = [row[0] for row in list(db.engine.execute(unseen_ids))]
    return Reminder.query.filter(Reminder.id.in_(unseen_list)).all()  # type: ignore


def get_recent_task_completions(
    user: User, date_start: datetime.date = today() - datetime.timedelta(days=7)
) -> List[Task]:
    log_task_pair = (
        db.session.query(TaskLog, Task)
        .outerjoin(Task)
        .filter(TaskLog.user_id == user.id)
        .filter(TaskLog.action == "complete")
        .filter(TaskLog.at >= date_start)
        .order_by(TaskLog.at.desc())  # type: ignore
        .all()
    )
    return [tlog.task_name or task.title for tlog, task in log_task_pair]


def get_current_median_skew(user: User) -> Optional[float]:
    if not user.current_time_zone:
        return None
    user_local_date = datetime.datetime.now(pytz.timezone(user.current_time_zone)).date()
    tasks = Task.query.filter_by(user_id=int(user.id)).all()
    if not tasks:
        return None
    skews = [task.calculate_skew(user_local_date, ignore_deferral=True) for task in tasks]
    return round(statistics.median(skews) * 100)


def get_reminders_from_this_week(user: User) -> List[Reminder]:
    notification_reminder_pair = (
        db.session.query(ReminderNotification, Reminder)
        .join(ReminderNotification)
        .filter(Reminder.user_id == user.id)
        .filter(ReminderNotification.sent_at >= today() - datetime.timedelta(days=7))
        .order_by(ReminderNotification.sent_at.desc())  # type: ignore
        .all()
    )
    return [r for _, r in notification_reminder_pair][:7]


def get_most_recent_reminder(user: User) -> Optional[Reminder]:
    prepared_sql = f"""select reminder_id
from reminder_notifications
         join reminders r on reminder_notifications.reminder_id = r.id
where user_id = {user.id}
order by sent_at desc
limit 1"""
    reminders = list(db.engine.execute(prepared_sql))
    if reminders:
        most_recent_reminder_id = reminders[0][0]
        return Reminder.query.filter_by(id=most_recent_reminder_id).one_or_none()
    return None


def send_and_log_notification(user: User, reminder_id: int, should_log: bool = True) -> None:
    reminder = Reminder.query.filter_by(id=reminder_id).one()
    if reminder.user_id != user.id:
        raise ValueError(f"User {user.username} does not own reminder with id {reminder.id}.")
    args = {
        "title": reminder.title,
        "message": reminder.message,
        "priority": -1,
        "html": 1,
    }
    if len(reminder.message) > 1000:
        args["message"] = f"{reminder.message[:1000]}..."
        args["url_title"] = "Read more..."
        args["url"] = f"https://zdone.co/reminders/{reminder.id}"
    get_pushover_client(user).send_message(**args)
    log(f"Sent notification {reminder.title}: {reminder.message}" f" to clients for user {user.username}.")
    if should_log:
        notification = ReminderNotification(
            reminder_id=reminder.id, sent_at=datetime.datetime.utcnow(), sent_via="pushover"
        )
        db.session.add(notification)
        db.session.commit()
