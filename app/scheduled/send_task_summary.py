import datetime

import pytz
import sendgrid
from jinja2 import Environment, PackageLoader, select_autoescape, StrictUndefined
from sendgrid.helpers.mail import *

from app import kv
from app.log import log
from app.models.base import User
from app.reminders import get_reminders_from_this_week, get_task_completions_from_this_week

env: Environment = Environment(
    loader=PackageLoader('app', 'email_templates'),
    autoescape=select_autoescape(['html', 'xml']),
    undefined=StrictUndefined
)
if __name__ == '__main__':
    sg = sendgrid.SendGridAPIClient(api_key=kv.get('SENDGRID_API_KEY'))
    from_email = Email("notifications@zdone.co", "zdone Notifications")
    subject = "Weekly zdone Summary"

    for user in User.query.filter(User.pushover_user_key.isnot(None)).all():  # type: ignore
        if datetime.datetime.now(pytz.timezone(user.current_time_zone)).weekday() != 5:
            log(f"Will not send to {user.username} because it is not Saturday "
                f"in their selected time zone ({user.current_time_zone}).")
            continue
        to_email = To(user.email)
        reminders = get_reminders_from_this_week(user)
        tasks = get_task_completions_from_this_week(user)
        if reminders or tasks:
            content = Content("text/html", env.get_template("reminders.html").render(
                reminders=reminders,
                tasks=tasks,
            ))
            mail = Mail(from_email, to_email, subject, content)
            response = sg.client.mail.send.post(request_body=mail.get())
