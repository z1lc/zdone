from app import db
from app.log import log
from app.models import User

from app.reminders import send_and_log_notification

# This code is scheduled to run once daily by the Heroku Scheduler
if __name__ == '__main__':
    log('Will send a single notification to everyone who has a Pushover user key.')
    for user in User.query.filter(User.pushover_user_key.isnot(None)).all():  # type: ignore
        # select the reminder with the least total amount of existing notifications, breaking ties by preferring
        # reminders with the longest time since last notification.
        # Also, avoid re-sending notifications that you just sent in the last 2 days
        prepared_sql = f"""with reminder_notifications_joined as (
    select r.id as reminder_id, rn.id as notification_id, user_id, title, active, sent_at
    from reminders r
             left join reminder_notifications rn on r.id = rn.reminder_id
),
    last_two_notifications as (
        select reminder_id
        from reminder_notifications_joined
        where user_id = {user.id} and reminder_id is not null
        order by sent_at desc
        limit 2
    )
select reminder_id, title, count(*), coalesce(max(sent_at), '2020-01-01')
from reminder_notifications_joined
where active and user_id = {user.id} and reminder_id not in (select * from last_two_notifications)
group by 1, 2
order by 3 asc, 4 asc;"""
        oldest_reminder_id = list(db.engine.execute(prepared_sql))[0][0]
        # log(f"would have sent reminder id {oldest_reminder_id} for user {user.username}")
        send_and_log_notification(user, oldest_reminder_id)
