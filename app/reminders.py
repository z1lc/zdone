import datetime
from typing import List, Optional

from pushover import Client

from app import kv, db
from app.log import log
from app.models.base import User
from app.models.tasks import Reminder, ReminderNotification


def get_reminders(user: User) -> List[Reminder]:
    return Reminder.query.filter_by(user_id=user.id).all()


def get_most_recent_reminder(user: User) -> Optional[Reminder]:
    prepared_sql = f"""select reminder_id
from reminder_notifications
         join reminders r on reminder_notifications.reminder_id = r.id
where user_id = {user.id}
order by sent_at desc
limit 1"""
    most_recent_reminder_id = list(db.engine.execute(prepared_sql))[0][0]
    return Reminder.query.filter_by(id=most_recent_reminder_id).one_or_none()


def send_and_log_notification(user: User, reminder_id: int, should_log: bool = True) -> None:
    reminder = Reminder.query.filter_by(id=reminder_id).one()
    if reminder.user_id != user.id:
        raise ValueError(f'User {user.username} does not own reminder with id {reminder.id}.')
    client = Client(user.pushover_user_key, api_token=kv.get('PUSHOVER_API_TOKEN'))
    args = {
        'title': reminder.title,
        'message': reminder.message,
        'priority': -1,
        'html': 1,
    }
    if len(reminder.message) > 1000:
        args['message'] = reminder.message[:1000] + "..."
        args['url_title'] = "Read more..."
        args['url'] = f"https://zdone.co/reminders/{reminder.id}"
    client.send_message(**args)
    log(f'Sent notification {reminder.title}: {reminder.message}'
        f' to clients for user {user.username}.')
    if should_log:
        notification = ReminderNotification(
            reminder_id=reminder.id,
            sent_at=datetime.datetime.utcnow(),
            sent_via="pushover"
        )
        db.session.add(notification)
        db.session.commit()
