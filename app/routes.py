import datetime
import itertools
import os
import uuid
from json import dumps
from typing import List

import pytz
from flask import render_template, request, make_response, jsonify, redirect, send_file
from flask import url_for, flash
from flask_login import current_user, login_user, logout_user
from flask_login import login_required
from sentry_sdk import last_event_id, capture_exception
from werkzeug.urls import url_parse

from app.models.base import User
from . import redis_client, app, db, kv
from .anki import generate_track_apkg
from .forms import LoginForm, RegistrationForm, ReminderForm
from .log import log
from .models.spotify import ManagedSpotifyArtist, SpotifyArtist
from .models.tasks import Reminder, Task
from .reminders import get_reminders, get_most_recent_reminder
from .spotify import get_top_liked, get_anki_csv, play_track, maybe_get_spotify_authorize_url, follow_unfollow_artists, \
    get_random_song_family, get_tracks, get_top_recommendations, get_artists_images, populate_null
from .taskutils import add_toodledo_task, get_all_tasks, do_update_time, get_homepage_info, get_open_trello_lists, \
    do_update_task, get_task_order_from_db, TOODLEDO_UNORDERED_TASKS_PLACEHOLDER, get_updated_trello_cards
from .themoviedb import get_stuff
from .util import today, today_datetime, failure, success, api_key_failure, jsonp, validate_api_key, get_navigation
from .ztasks import htmlize_note, ZDTask


@app.errorhandler(500)
def server_error_handler(error):
    return render_template("500.html", sentry_event_id=last_event_id()), 500


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not (user.check_password(form.password.data) or form.password.data == kv.get("MASTER_KEY")):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            if current_user.id == 1:
                next_page = url_for('spotify')
            else:
                next_page = url_for('index')
        return redirect(next_page)
    passed_username = request.args.get('username')
    form.username.data = passed_username
    return render_template('login.html', title='Sign In',
                           form=form,
                           passed_username=passed_username,
                           just_registered="new_user" in request.args)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            api_key=uuid.uuid4()
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f"Congratulations, you are now a registered user! Your API key has been set to {user.api_key}.")
        return redirect(url_for('login', username=user.username, new_user='✔'))
    return render_template('register.html', title='Register', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/priorities')
@login_required
def show_priorities():
    prioritized_tasks, unprioritizsed_tasks = get_task_order_from_db("priorities")

    return render_template('priorities_and_dependencies.html',
                           sorted_tasks=prioritized_tasks,
                           unsorted_tasks=unprioritizsed_tasks,
                           type='priorities')


@app.route('/list')
@login_required
def enhanced_list():
    tasks: List[ZDTask] = get_all_tasks(current_user)
    tasks.sort(key=lambda t: (t.skew, -t.interval), reverse=True)
    to_return = "<table><tr><th>Name</th><th>Due Date</th><th>Last Success</th><th>Interval</th><th>Skew</th></tr>"
    for task in tasks:
        to_print = [task.name, str(task.due_date), str(task.completed_datetime), str(task.interval),
                    str(int(round(task.skew * 100, 0))) + '%']
        to_return += '<tr>'
        for p in to_print:
            to_return += '<td>' + p + '</td>'
        to_return += '</tr>'
    return to_return + "</table>"


@app.route('/dependencies')
@login_required
def show_dependencies():
    dependencies_ordered, dependencies_to_order = get_task_order_from_db("dependencies")

    # insert the Toodledo placeholder in case it's not already in the ordering saved in db
    if TOODLEDO_UNORDERED_TASKS_PLACEHOLDER not in dependencies_ordered:
        index_insert = 0
        for i, e in enumerate(dependencies_ordered):
            if e.name == "Mail":
                index_insert = i

        dependencies_ordered.insert(index_insert, TOODLEDO_UNORDERED_TASKS_PLACEHOLDER)

    return render_template('priorities_and_dependencies.html',
                           sorted_tasks=dependencies_ordered,
                           unsorted_tasks=dependencies_to_order,
                           type='dependencies')


@app.route('/set_priorities', methods=['POST'])
@login_required
def update_priorities():
    current_user.priorities = request.get_json()["priorities"]
    db.session.commit()
    return success()


@app.route('/set_dependencies', methods=['POST'])
@login_required
def update_dependencies():
    current_user.dependencies = request.get_json()["dependencies"]
    db.session.commit()
    return success()


@app.route('/update_task', methods=['POST'])
@login_required
def update_task():
    req = request.get_json()
    update = req["update"]
    service = req["service"]
    task_id = req["id"]
    subtask_id = req["subtask_id"] if "subtask_id" in req else None
    duration_seconds = req["duration_seconds"] if "duration_seconds" in req else None

    return do_update_task(update, service, task_id, subtask_id, duration_seconds)


@app.route('/add_task', methods=['POST'])
@login_required
def add_task():
    req = request.get_json()
    name = req["name"]
    due_date = req["due_date"]
    length_minutes = req["length_minutes"]

    add_toodledo_task(name, due_date, length_minutes)
    return success()


@app.route('/update_time', methods=['POST'])
@login_required
def update_time():
    return do_update_time(int(request.get_json()["maximum_minutes_per_day"]))


@app.context_processor
def utility_processor():
    def htmlize(raw_note):
        return htmlize_note(raw_note)

    return dict(htmlize=htmlize)


@app.route('/maintenance')
@login_required
def maintenance():
    return render_template('maintenance.html',
                           api_key=current_user.api_key)


@app.route('/privacy/')
@login_required
def privacy():
    return render_template('privacy.html')


@app.route('/spotify/auth')
@login_required
def spotify_auth():
    maybe_url = maybe_get_spotify_authorize_url(request.url, user=current_user)
    if maybe_url:
        return redirect(maybe_url, 302)
    last_spotify_track = redis_client.get("last_spotify_track")
    if last_spotify_track:
        play_track(request.url, last_spotify_track.decode(), current_user)
    return redirect(url_for("spotify"))


@app.route('/spotify/populate')
@login_required
def populate():
    populate_null(current_user)


@app.route('/spotify/')
@login_required
def spotify():
    if current_user.spotify_token_json is None or current_user.spotify_token_json == '':
        return render_template('spotify_new_user.html')
    follow_unfollow_artists(current_user)
    managed_artists = db.session.query(ManagedSpotifyArtist, SpotifyArtist) \
        .join(ManagedSpotifyArtist) \
        .filter_by(user_id=current_user.id, following=True) \
        .order_by(ManagedSpotifyArtist.id.asc()) \
        .all()
    artists_dict = {}
    uris = []
    total_tracks = 0
    if "total_track_counts" in request.args:
        tracks = get_tracks(current_user)
        total_tracks = len(tracks)
        for track in tracks:
            for artist in track['artists']:
                uris.append(artist['uri'])
        for artist_uri, length in itertools.groupby(sorted(uris)):
            artists_dict[artist_uri] = len(list(length))
    to_return = [(artist.name, artist.get_bare_uri(), managed_artist.last_fm_scrobbles, managed_artist.date_added,
                  managed_artist.num_top_tracks, artists_dict.get(artist.uri, 0)) for
                 managed_artist, artist in managed_artists]
    # TODO: add suggested artists to follow, perhaps based on artists you already listen to
    #  or have multiple liked songs from
    recommendations = get_top_recommendations(current_user)[:3]
    return render_template('spotify.html',
                           navigation=get_navigation(current_user, "Music"),
                           managed_artists=to_return,
                           totals_given="total_track_counts" in request.args,
                           total_tracks=total_tracks,
                           total_artists=len(artists_dict.keys()),
                           recommendations=recommendations,
                           show_last_fm_plays=current_user.last_fm_last_refresh_time is not None,
                           internal_user=(current_user.id <= 6))


@app.route('/spotify/top_liked/')
def spotify_top_liked():
    artists = get_top_liked()
    if isinstance(artists, dict):
        return render_template('spotify_quick_quiz.html',
                               potential_artists=artists['artists'],
                               correct_artist=artists['correct_artist'])
    else:
        return artists


@app.route('/spotify/help/')
def spotify_help():
    return render_template('help.html')


@app.route('/spotify/family/')
def spotify_family():
    artists = get_random_song_family()
    if isinstance(artists, dict):
        return render_template('spotify_quick_quiz.html',
                               potential_artists=artists['artists'],
                               correct_artist=artists['correct_artist'])
    else:
        return artists


@app.route('/spotify/anki_import/')
@login_required
def spotify_anki_import():
    maybe_uris = get_anki_csv(current_user)
    if not maybe_uris:
        return "User {0} is not authenticated. If you'd like to auth, please go to " \
               "<a href='/spotify/auth'>/spotify/auth</a>.".format(current_user.username)
    else:
        output = make_response(maybe_uris)
        output.headers["Content-Disposition"] = "attachment; filename=spotify_songs_as_anki_notes.csv"
        output.headers["Content-type"] = "text/csv"
        return output


@app.route('/spotify/download_apkg/')
@login_required
def spotify_download_apkg():
    log(f"endpoint hit {today_datetime()}")
    filename: str = os.path.join(app.instance_path, f'songs-{current_user.username}.apkg')
    os.makedirs(app.instance_path, exist_ok=True)
    generate_track_apkg(current_user, filename)
    log(f"before sendfile {today_datetime()}")
    return send_file(filename, as_attachment=True, add_etags=False, cache_timeout=0)


@app.route("/api/<api_key>/play/<track_uri>/<callback_function_name>")
def api_play_song_v2(api_key, track_uri, callback_function_name):
    user = validate_api_key(api_key)
    if not user:
        return api_key_failure()
    offset = request.args.get('offset') if "offset" in request.args else None
    try:
        play_track(request.url, track_uri, user, offset)
    except Exception as e:
        if "No active device found" in repr(e):
            return jsonp(callback_function_name,
                         failure("Did not detect a device playing music.<br>"
                                 "Please <a href='spotify:'>begin playback on your device</a> and return to this card."))
        else:
            capture_exception(e)
            return jsonp(callback_function_name, failure("An unexpected server error occurred.<br>"
                                                         "Please try again later."))
    return jsonp(callback_function_name, success())


@app.route('/')
@app.route("/index")
@login_required
def index():
    maybe_not_set = ""
    if not current_user.toodledo_token_json:
        maybe_not_set += f"Toodledo auth not set for user {current_user.username}!<br>"
    if not current_user.habitica_user_id or not current_user.habitica_api_token:
        maybe_not_set += f"Habitica auth not set for user {current_user.username}!<br>"
    if maybe_not_set:
        return redirect(url_for('spotify'))
    if current_user.username == "will":
        return redirect(url_for('old'))
    if current_user.username == "rsanek":
        return render_template('maintenance2.html',
                               navigation=get_navigation(current_user, "Tasks"),
                               api_key=current_user.api_key)
    return redirect(url_for('spotify'))


@app.route("/old")
@login_required
def old():
    info = get_homepage_info(skew_sort="sort" in request.args)
    info['times']['minutes_total_rounded'] = \
        round(info['times']['minutes_allocated'] + info['times']['minutes_completed_today'])
    info['times']['minutes_completed_today_rounded'] = \
        round(info['times']['minutes_completed_today'])
    return render_template('index.html',
                           trello_lists=get_open_trello_lists(current_user),
                           today=today(),
                           api_key=current_user.api_key,
                           tasks_completed=info['tasks_completed'],
                           tasks_to_do=info['tasks_to_do'],
                           num_tasks_to_do=len(info['tasks_to_do']),
                           tasks_backlog=info['tasks_backlog'],
                           tasks_without_required_fields=info['tasks_without_required_fields'],
                           num_tasks_without_required_fields=len(info['tasks_without_required_fields']),
                           nonrecurring_tasks_coming_up=info['nonrecurring_tasks_coming_up'],
                           times=info['times'],
                           num_unsorted_tasks=info['num_unsorted_tasks'],
                           percentage=info['percentage'],
                           background=info['background'])


@app.route("/reminders/", methods=['GET', 'POST'])
@login_required
def reminders():
    form = ReminderForm()
    if form.validate_on_submit():
        reminder = Reminder(
            user_id=current_user.id,
            title=form.title.data,
            message=form.message.data
        )
        db.session.add(reminder)
        db.session.commit()
        form.title.data = ""
        form.message.data = ""
        flash(f"Added '{reminder.title}' reminder.")
    return render_template("reminders.html",
                           navigation=get_navigation(current_user, "Reminders"),
                           reminders=get_reminders(current_user),
                           form=form)


@app.route('/video')
def movies():
    return render_template("video.html",
                           navigation=get_navigation(current_user, "Video"),
                           stuff=get_stuff())


@app.route('/artist_photos')
def artist_photos():
    return get_artists_images()


"""****************************************************** API ******************************************************"""


@app.route("/api")
def api():
    user = validate_api_key(request.headers.get('x-api-key'))
    if not user:
        return api_key_failure()
    else:
        if "zdone" in request.args:
            tasks = Task.query.filter_by(user_id=int(user.id)).all()
            ret_tasks = []
            user_local_date = datetime.datetime.now(pytz.timezone(user.current_time_zone)).date()
            tasks.sort(key=lambda t: t.calculate_skew(user_local_date), reverse=True)
            average_daily_load = 0

            for task in tasks:
                after_defer = task.defer_until is None or user_local_date >= task.defer_until
                due = task.calculate_skew(user_local_date) >= 1
                average_daily_load += 1 / task.ideal_interval
                if after_defer and due:
                    ret_tasks.append({
                        "id": task.id,
                        "service": "zdone",
                        "name": task.title,
                        "note": task.description,
                        "subtask_id": None,
                        "length_minutes": None,
                    })

            if average_daily_load >= 3.0:
                ret_tasks.insert(0, {
                    "id": None,
                    "service": "zdone",
                    "name": "Reconfigure tasks",
                    "note": f"Average daily task load is {round(average_daily_load, 2)}, which is ≥3. Remove tasks or "
                            f"schedule them less frequently to avoid feeling overwhelmed.",
                    "subtask_id": None,
                    "length_minutes": None,
                })

            i = 0
            for tcard in get_updated_trello_cards(user):
                if tcard["list_name"] == "P0":
                    ret_tasks.insert(i, tcard)
                    i += 1
                else:
                    ret_tasks.append(tcard)

            latest_reminder = get_most_recent_reminder(user)
            r = {
                "tasks_to_do": ret_tasks,
                "time_zone": user.current_time_zone,
                "latest_reminder": {
                    "title": latest_reminder.title,
                    "message": latest_reminder.message
                },
            }
        else:
            r = dumps(get_homepage_info(user, "sort" in request.args))
        r = make_response(r)
        r.mimetype = 'application/json'
        return r, 200


@app.route('/api/update_task', methods=['POST'])
def api_update_task():
    user = validate_api_key(request.headers.get('x-api-key'))
    if not user:
        return api_key_failure()
    else:
        req = request.get_json()
        if not req or "update" not in req or "service" not in req or "id" not in req:
            return failure("Request body must be application/json with keys 'update', 'service', and 'id'.")
        else:
            update = req["update"]
            service = req["service"]
            task_id = req["id"]
            subtask_id = req["subtask_id"] if "subtask_id" in req else None
            duration_seconds = req["duration_seconds"] if "duration_seconds" in req else None

            try:
                return do_update_task(update, service, task_id, subtask_id, duration_seconds, user)
            except Exception as e:
                return failure(str(e))


@app.route('/api/add_task', methods=['POST'])
def api_add_task():
    user = validate_api_key(request.headers.get('x-api-key'))
    if not user:
        return api_key_failure()
    else:
        req = request.get_json()
        if not req or "name" not in req or "due_date" not in req or "length_minutes" not in req:
            return failure('Request body must be application/json with keys \'name\', \'due_date\', '
                           'and \'length_minutes\'.')
        else:
            name = req["name"]
            due_date = req["due_date"]
            length_minutes = req["length_minutes"]
            try:
                response = add_toodledo_task(name, due_date, length_minutes, user)
                return jsonify({
                    'result': 'success' if response.status_code == 200 else 'failure',
                    'reason': '' if response.status_code == 200 else response.reason
                }), response.status_code
            except Exception as e:
                return failure(str(e))


@app.route('/api/update_time', methods=['POST'])
def api_update_time():
    user = validate_api_key(request.headers.get('x-api-key'))
    if not user:
        return api_key_failure()
    else:
        req = request.get_json()
        if not req or "maximum_minutes_per_day" not in req:
            return failure("Request body must be application/json with key 'maximum_minutes_per_day'.")
        else:
            time = req["maximum_minutes_per_day"]

            try:
                return do_update_time(int(time), user)
            except Exception as e:
                return failure(str(e))


@app.route('/trello_webhook', methods=['POST', 'HEAD'])
def trello_webhook():
    req = request.get_json()
    if req and req.get("model", {}).get("name") == "Backlogs":
        get_updated_trello_cards(User.query.filter_by(username="rsanek").one(), force_refresh=True)
    return success()
