import itertools
import os
import uuid
from datetime import timedelta, datetime
from json import dumps
from typing import List, Tuple, Optional

from flask import render_template, request, make_response, jsonify, redirect, send_file
from flask import url_for, flash
from flask_login import current_user, login_user, logout_user
from flask_login import login_required
from sentry_sdk import last_event_id
from trello import TrelloClient
from werkzeug.urls import url_parse

from . import redis_client, app, db, socketio, kv
from .anki import generate_track_apkg
from .forms import LoginForm, RegistrationForm
from .models import User, TaskCompletion, ManagedSpotifyArtist, SpotifyArtist
from .spotify import get_top_liked, get_anki_csv, play_track, maybe_get_spotify_authorize_url, \
    populate_null_artists, follow_unfollow_artists, \
    get_random_song_family, get_tracks, update_last_fm_scrobble_counts, get_top_recommendations, get_artists_images
from .taskutils import get_toodledo_tasks, get_habitica_tasks, complete_habitica_task, complete_toodledo_task, \
    add_toodledo_task
from .themoviedb import get_stuff
from .util import today, today_datetime
from .ztasks import ZDTask, htmlize_note


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


TOODLEDO_UNORDERED_TASKS_PLACEHOLDER = ZDTask(
    "-1", "[all unordered Toodledo Tasks]", 0, None, None, "", "", "unorderedToodledo", [])


@app.route('/list')
@login_required
def enhanced_list():
    tasks = get_all_tasks(current_user)
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


def get_all_tasks(user: User = current_user) -> List[ZDTask]:
    return get_toodledo_tasks(redis_client, user) + get_habitica_tasks(user)


def get_task_order_from_db(order_type, user: User = current_user) -> Tuple[List[ZDTask], List[ZDTask]]:
    currently_sorted_in_db = getattr(user, order_type)
    if currently_sorted_in_db:
        currently_sorted_in_db = currently_sorted_in_db.split("|||")
    else:
        currently_sorted_in_db = []
    sorted_tasks, unsorted_tasks = [], []
    all_tasks: List[ZDTask] = get_all_tasks(user)
    task_map = {t.name: t for t in all_tasks}
    task_map[TOODLEDO_UNORDERED_TASKS_PLACEHOLDER.name] = TOODLEDO_UNORDERED_TASKS_PLACEHOLDER
    for name in currently_sorted_in_db:
        if name in task_map:
            sorted_tasks.append(task_map[name])
            del task_map[name]

    for task in task_map.values():
        if task.is_repeating():
            unsorted_tasks.append(task)

    if TOODLEDO_UNORDERED_TASKS_PLACEHOLDER in unsorted_tasks:
        del unsorted_tasks[unsorted_tasks.index(TOODLEDO_UNORDERED_TASKS_PLACEHOLDER)]

    return sorted_tasks, unsorted_tasks


def success():
    return jsonify({
        'result': 'success'
    }), 200


def failure(reason="", code=400):
    return jsonify({
        'result': 'failure',
        'reason': reason
    }), code


def api_key_failure():
    return failure("Make sure you are passing a valid API key in the x-api-key header.", 401)


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


def do_update_task(update, service, task_id, subtask_id, duration_seconds=0, user: User = current_user):
    if update == "defer":
        redis_client.append("hidden:" + user.username + ":" + str(today()), (task_id + "|||").encode())
        redis_client.expire("hidden:" + user.username + ":" + str(today()), timedelta(days=7))
        # can no longer use cached tasks since we have to re-sort
        redis_client.delete("toodledo:" + user.username + ":last_mod")
    elif update == "complete":
        if service == "habitica":
            complete_habitica_task(task_id, subtask_id, user)
        elif service == "toodledo":
            if subtask_id:
                complete_toodledo_task(subtask_id, user)
            else:
                complete_toodledo_task(task_id, user)
        else:
            return failure(f"unexpected service type '{service}'")

        task_completion = TaskCompletion(user_id=user.id, service=service, task_id=task_id, subtask_id=subtask_id,
                                         duration_seconds=duration_seconds, at=datetime.now())
        db.session.add(task_completion)
        db.session.commit()
    else:
        return failure(f"unexpected update type '{update}'")

    length = 0.0
    if not subtask_id:
        length = [t.length_minutes for i, t in enumerate(get_all_tasks(user))
                  if t.service == service and t.id == task_id][0]
    socketio.emit(user.api_key, {
        'update': update,
        'service': service,
        'task_id': task_id,
        'subtask_id': subtask_id if subtask_id else '',
        'length_minutes': length
    })
    return success()


def do_update_time(time, user: User = current_user):
    user.maximum_minutes_per_day = max(0, min(1440, int(time)))
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
    return do_update_time(request.get_json()["maximum_minutes_per_day"])


def get_homepage_info(user: User = current_user, skew_sort=False):
    minutes_completed_today = 0.0
    tasks_completed, tasks_to_do, tasks_backlog, nonrecurring_tasks_coming_up = [], [], [], []
    prioritized_tasks, unprioritized_tasks = get_task_order_from_db("priorities", user)
    for task in prioritized_tasks:
        if task.completed_today() and task not in tasks_completed:
            minutes_completed_today += task.length_minutes
            tasks_completed.append(task)

    task_ids_to_hide = redis_client.get("hidden:" + user.username + ":" + str(today()))
    task_ids_to_hide = [] if task_ids_to_hide is None else task_ids_to_hide.decode().split("|||")

    total_minutes = user.maximum_minutes_per_day
    minutes_left_to_schedule = total_minutes - minutes_completed_today

    i = 0
    minutes_allocated = 0.0
    all_tasks = get_all_tasks(user)
    # try sorting by skew
    if skew_sort:
        all_tasks.sort(key=lambda t: (t.skew, -t.interval), reverse=True)
    while i < len(all_tasks):
        task = all_tasks[i]
        if task.id not in task_ids_to_hide \
                and not task.completed_today():
            if task.due_date is not None and task.due_date <= today():
                # add 4 minutes to allow some space for non-round-number tasks to be scheduled
                if task.length_minutes <= (minutes_left_to_schedule + 4) and task not in tasks_to_do:
                    tasks_to_do.append(task)
                    minutes_left_to_schedule -= task.length_minutes
                    minutes_allocated += task.length_minutes
                elif task not in tasks_backlog:
                    tasks_backlog.append(task)
            elif not task.is_repeating() and \
                    (task.due_date is not None and task.due_date <= (today() + timedelta(days=1))) and \
                    task not in nonrecurring_tasks_coming_up:
                nonrecurring_tasks_coming_up.append(task)
        i += 1

    ordering = [t.name for t in get_task_order_from_db("dependencies", user)[0]]
    sorted_tasks_to_do: List[Tuple[int, ZDTask]] = []  # int in Tuple is priority; lower is better
    for task in tasks_to_do:
        if task.name in ordering:
            sorted_tasks_to_do.append((ordering.index(task.name), task))
        else:
            sorted_tasks_to_do.append((ordering.index(TOODLEDO_UNORDERED_TASKS_PLACEHOLDER.name)
                                       if TOODLEDO_UNORDERED_TASKS_PLACEHOLDER.name in ordering else 0,
                                       task))

    sorted_tasks_to_do.sort(key=lambda tup: tup[0])

    times = {
        'minutes_completed_today': minutes_completed_today,
        'minutes_allocated': minutes_allocated,
        'maximum_minutes_per_day': user.maximum_minutes_per_day
    }
    denom = times['minutes_completed_today'] + times['minutes_allocated']
    percent_done = int(times['minutes_completed_today'] * 100 / denom) if denom > 0 else 0
    tasks_without_required_fields = get_tasks_without_required_fields(all_tasks)
    return {
        "tasks_completed": list(tasks_completed),
        "tasks_to_do": tasks_to_do if skew_sort else [task for _, task in sorted_tasks_to_do],
        "tasks_backlog": list(tasks_backlog),
        "tasks_without_required_fields": tasks_without_required_fields,
        "nonrecurring_tasks_coming_up": list(nonrecurring_tasks_coming_up),
        "times": times,
        "num_unsorted_tasks": len(unprioritized_tasks),
        "percentage": min(100, max(0, percent_done)),
        "background": "red !important" if times['minutes_completed_today'] < 30 else "#2196F3 !important"
    }


def get_tasks_without_required_fields(all_tasks):
    bad_tasks = []
    for task in all_tasks:
        if task.completed_datetime is None:
            if (task.length_minutes is None or task.length_minutes == 0) or \
                    task.due_date is None:
                bad_tasks.append(task)

    return bad_tasks


def get_open_trello_lists():
    if current_user.trello_api_key and current_user.trello_api_access_token:
        client = TrelloClient(
            api_key=current_user.trello_api_key,
            api_secret=current_user.trello_api_access_token
        )
        backlog_board = [board for board in client.list_boards() if board.name == 'Backlogs'][0]

        return backlog_board.list_lists('open')
    return []


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
    populate_null_artists(current_user)


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
        update_last_fm_scrobble_counts(current_user)
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
    print(f"endpoint hit {today_datetime()}")
    filename: str = os.path.join(app.instance_path, f'songs-{current_user.username}.apkg')
    os.makedirs(app.instance_path, exist_ok=True)
    generate_track_apkg(current_user, filename)
    print(f"before sendfile {today_datetime()}")
    return send_file(filename, as_attachment=True, add_etags=False, cache_timeout=0)


# TODO: remove this endpoint once people are migrated off
@app.route("/api/play_track")
def api_play_song():
    args = request.args
    if not args or "track_uri" not in args or "api_key" not in args:
        return failure("Request must set parameters 'track_uri' and 'api_key'.")
    else:
        track_uri = args.get('track_uri')
        api_key = args.get('api_key')
        api_play_song_v2(api_key, track_uri, "no_function")
        return success()


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
    return jsonp(callback_function_name, success())


def jsonp(function_name, payload):
    if isinstance(payload, str):
        return f"{function_name}({payload})"
    elif isinstance(payload, tuple):
        # we've received payload from a success() or failure() method
        payload = payload[0].get_data().decode('utf-8').replace('\n', '')
        return f"{function_name}({payload})"


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
    info = get_homepage_info(skew_sort="sort" in request.args)
    info['times']['minutes_total_rounded'] = \
        round(info['times']['minutes_allocated'] + info['times']['minutes_completed_today'])
    info['times']['minutes_completed_today_rounded'] = \
        round(info['times']['minutes_completed_today'])
    return render_template('index.html',
                           trello_lists=get_open_trello_lists(),
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


def validate_api_key(api_key: str) -> Optional[User]:
    return User.query.filter_by(api_key=api_key).one() if api_key else None


@app.route("/api")
def api():
    user = validate_api_key(request.headers.get('x-api-key'))
    if not user:
        return api_key_failure()
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
                return do_update_time(time, user)
            except Exception as e:
                return failure(str(e))


@app.route('/movies')
def movies():
    return get_stuff()


@app.route('/artist_photos')
def artist_photos():
    return get_artists_images()
