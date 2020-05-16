import datetime

from pushover import Client

from app import kv, db
from app.models import Reminder, User, ReminderNotification

# This code is scheduled to run once daily by the Heroku Scheduler
if __name__ == '__main__':
    print('Will send a single notification to everyone who has a Pushover user key.')
    for user in User.query.filter(User.pushover_user_key.isnot(None)).all():  # type: ignore
        prepared_sql = f"""select r.id
from reminders r
         left join reminder_notifications rn on r.id = rn.reminder_id
where r.active and user_id={user.id}
group by 1
order by coalesce(max(rn.sent_at), '2020-01-01') asc
limit 1;"""
        oldest_reminder_id = list(db.engine.execute(prepared_sql))[0][0]
        oldest_reminder = Reminder.query.filter_by(id=oldest_reminder_id).one()
        client = Client(user.pushover_user_key, api_token=kv.get('PUSHOVER_API_TOKEN'))
        client.send_message(
            title=oldest_reminder.title,
            message=oldest_reminder.message
        )
        print(f'Sent notification {oldest_reminder.title}: {oldest_reminder.message}'
              f' to clients for user {user.username}.')
        notification = ReminderNotification(
            reminder_id=oldest_reminder.id,
            sent_at=datetime.datetime.now(),
            sent_via="pushover"
        )
        db.session.add(notification)
        db.session.commit()
