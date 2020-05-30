import datetime

from pushover import Client

from app import kv, db
from app.models import Reminder, User, ReminderNotification


def send_and_log_notification(user: User, reminder_id: int, log: bool = True) -> None:
    reminder = Reminder.query.filter_by(id=reminder_id).one()
    if reminder.user_id != user.id:
        raise ValueError(f'User {user.username} does not own reminder with id {reminder.id}.')
    client = Client(user.pushover_user_key, api_token=kv.get('PUSHOVER_API_TOKEN'))
    client.send_message(
        title=reminder.title,
        message=reminder.message,
        priority=-1,
        # url_title='Tap to re-learn habit',
        # url="https://zdone.co/reset/" + str(reminder_id)
    )
    print(f'Sent notification {reminder.title}: {reminder.message}'
          f' to clients for user {user.username}.')
    if log:
        notification = ReminderNotification(
            reminder_id=reminder.id,
            sent_at=datetime.datetime.now(),
            sent_via="pushover"
        )
        db.session.add(notification)
        db.session.commit()