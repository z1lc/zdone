from app import db
from app.models import User

from app.notification import send_and_log_notification

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
        send_and_log_notification(user, oldest_reminder_id)
