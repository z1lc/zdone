import random

from app import db
from app.log import log
from app.models.base import User
from app.models.tasks import Reminder
from app.reminders import send_and_log_notification

MINIMUM_DAYS_BETWEEN_NOTIFICATION_FOR_SAME_REMINDER = 2
MAXIMUM_DAYS_BETWEEN_NOTIFICATION_FOR_SAME_REMINDER = 14

# This code is scheduled to run once daily by the Heroku Scheduler
if __name__ == '__main__':
    log('Will send a single notification to everyone who has a Pushover user key.')
    for user in User.query.filter(User.pushover_user_key.isnot(None)).all():  # type: ignore
        num_active_reminders = Reminder.query.filter_by(user_id=user.id, active=True).count()
        last_n_to_ignore = max(
            min(num_active_reminders // 2,
                MAXIMUM_DAYS_BETWEEN_NOTIFICATION_FOR_SAME_REMINDER),
            MINIMUM_DAYS_BETWEEN_NOTIFICATION_FOR_SAME_REMINDER)

        valid_potential_reminders_to_be_sent_with_counts = f"""
with reminder_notifications_joined as (
    select r.id as reminder_id, rn.id as notification_id, user_id, title, active, sent_at
    from reminders r
             left join reminder_notifications rn on r.id = rn.reminder_id
),
    last_n_notifications as (
        select reminder_id
        from reminder_notifications_joined
        where user_id = {user.id} and reminder_id is not null and sent_at is not null
        order by sent_at desc
        limit {last_n_to_ignore}
    )
select reminder_id, title, count(sent_at), coalesce(max(sent_at), '2020-01-01')
from reminder_notifications_joined
where active and user_id = {user.id} and reminder_id not in (select * from last_n_notifications)
group by 1, 2
order by 3 asc, 4 asc;"""
        potential_reminders = list(db.engine.execute(valid_potential_reminders_to_be_sent_with_counts))
        if potential_reminders:
            # there are a few requirements from the selection of the reminder:
            # * we don't want to repeat a recent reminder (handled by SQL above)
            # * we want to prefer reminders that we've seen less than reminders we've already seen more
            # * we don't want reminder selection to be predictable (same order / same day)
            # below, we opt for a two-stage randomness algorithm to achieve this,
            lowest_number_of_notifications = potential_reminders[0][2]
            highest_number_of_notifications = potential_reminders[-1][2]
            num_notifications_max_random_choice = random.choice(
                list(range(lowest_number_of_notifications, highest_number_of_notifications + 1)))
            potential_reminders = [p for p in potential_reminders if p[2] <= num_notifications_max_random_choice]
            selected_reminder_id = random.choice(potential_reminders)[0]
            log(f"Will send notification for reminder id {selected_reminder_id} for user {user.username}.")
            send_and_log_notification(user, selected_reminder_id)
        else:
            log(f"Did not find any acceptable reminders for user {user.username}.")
