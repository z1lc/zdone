import datetime

import pytz
import sendgrid
from jinja2 import Environment, PackageLoader, select_autoescape, StrictUndefined

from app import kv
from app.hn import get_hn_articles_from_this_week
from app.log import log
from app.models.base import User, GateDef
from app.reminders import (
    get_reminders_from_this_week,
    get_recent_task_completions,
    get_current_median_skew,
    get_reminders,
    get_unseen_reminders,
    get_current_median_number_of_reminder_notifications,
)
from app.spotify import get_distinct_songs_this_week, get_new_songs_this_week, get_new_this_week
from app.util import get_distinct_users_in_last_week

env: Environment = Environment(
    loader=PackageLoader("app", "email_templates"),
    autoescape=select_autoescape(["html", "xml"]),
    undefined=StrictUndefined,
)
from_email = sendgrid.Email("notifications@zdone.co", "zdone Notifications")
subject = "Weekly zdone Summary"


def send_email(user: User):
    sg = sendgrid.SendGridAPIClient(api_key=kv.get("SENDGRID_API_KEY"))
    to_email = sendgrid.To(user.email)
    reminders = get_reminders_from_this_week(user)
    tasks = get_recent_task_completions(user)
    articles = get_hn_articles_from_this_week(user)
    distinct_listens = get_distinct_songs_this_week(user)
    new_listens = get_new_songs_this_week(user)
    distinct_users = get_distinct_users_in_last_week()
    show_users = user.is_gated(GateDef.WEEKLY_ZDONE_SUMMARY_EMAIL_SHOW_USERS)

    if reminders or tasks:
        content = sendgrid.Content(
            "text/html",
            env.get_template("weekly_summary.html").render(
                reminders=reminders,
                tasks=tasks,
                num_tasks=len(tasks),
                skew=get_current_median_skew(user),
                articles=articles,
                num_articles=len(articles),
                distinct_listens=distinct_listens,
                new_listens=new_listens,
                artists=get_new_this_week(user)[:5],
                active_reminders=len([r for r in get_reminders(user) if r.active]),
                median_reminder_notifications=get_current_median_number_of_reminder_notifications(user),
                unseen_reminders=len(get_unseen_reminders(user)),
                num_distinct_users=len(distinct_users) if show_users else None,
                distinct_user_string=", ".join(distinct_users) if show_users else None,
            ),
        )
        mail = sendgrid.Mail(from_email, to_email, subject, content)
        sg.client.mail.send.post(request_body=mail.get())


if __name__ == "__main__":
    for user in User.query.filter(User.pushover_user_key.isnot(None)).all():  # type: ignore
        if datetime.datetime.now(pytz.timezone(user.current_time_zone)).weekday() != 5:
            log(
                f"Will not send to {user.username} because it is not Saturday "
                f"in their selected time zone ({user.current_time_zone})."
            )
            continue
        send_email(user)
