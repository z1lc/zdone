import datetime
from typing import List

import humanize
import pytz
from dateutil import parser
from pifx import PIFX
from suntime import Sun

from app import kv
from app.log import log

DAY_CONFIG = 5500, 1
EARLY_NIGHT_CONFIG = 2700, 0.6


def log_return(response: List):
    responded_lights = [l['label'] for l in response if l['status'] == 'ok']
    responded_lights.sort()
    log(f'   {len(responded_lights)} lights responded with "ok" status to change: {responded_lights}')
    non_responded_lights = [l['label'] for l in response if l['status'] != 'ok']
    non_responded_lights.sort()
    log(f'   {len(non_responded_lights)} lights responded with non-"ok" status to change: {non_responded_lights}')


def set_to(now: datetime.datetime, target: datetime.datetime, config, description: str):
    within_15_minutes = target - datetime.timedelta(minutes=15) < now < target
    are_or_are_not = "are" if within_15_minutes else "are not"
    log(f'We {are_or_are_not} within 15 minutes of target {description} time of {target.time()}.')
    if within_15_minutes:
        difference: float = round((target - now_pacific_time).total_seconds())
        kelvin, brightness = config
        log(f'Will attempt to change LIFX lights to {kelvin}K, {brightness} brightness over {difference} seconds.')
        log_return(p.set_state(color=f'kelvin:{kelvin} brightness:{brightness}', duration=str(difference)))


def print_status(p, show_old=False, tabbed=True):
    response = p.list_lights()
    response.sort(key=lambda light: light['label'])
    log('Current light statuses:')
    for light in response:
        diff = datetime.datetime.utcnow() - parser.parse(light['last_seen']).replace(tzinfo=None)
        if diff.days < 7 or show_old:
            connected_string = "connected" if light['connected'] else "disconnected"
            last_seen = humanize.naturaltime(diff)
            product_name = light['product']['name'] or "Unknown Product"
            beginning = "\t" if tabbed else ""
            log(f"{beginning}{light['label']} ({product_name}): {connected_string}, power {light['power']}"
                f" | {light['color']['kelvin']}K, {light['brightness']} brightness | last seen {last_seen}")


if __name__ == '__main__':
    log('Running LIFX cron...')
    p = PIFX(kv.get('LIFX_ACCESS_TOKEN'))
    sun = Sun(37.78, -122.42)  # SF lat/long
    now_pacific_time = datetime.datetime.now(pytz.timezone('America/Los_Angeles'))
    wake_up_datetime = now_pacific_time.replace(hour=8, minute=0, second=0, microsecond=0)
    sun_for_date = now_pacific_time.date() + datetime.timedelta(days=1) # not sure why you have to add a day?
    sunset_datetime = sun.get_local_sunset_time(date=sun_for_date, local_time_zone=pytz.timezone('America/Los_Angeles'))

    log(f'It is {now_pacific_time.time()}.')
    print_status(p)
    set_to(now_pacific_time, wake_up_datetime, DAY_CONFIG, 'wake up')
    set_to(now_pacific_time, sunset_datetime, EARLY_NIGHT_CONFIG, 'sunset')
