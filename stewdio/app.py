import json
import logging
import os
import random
from datetime import datetime
from functools import wraps
from urllib.parse import urlsplit, parse_qs, unquote, quote
from http import cookies

import flask
import gevent
import requests
import sqlalchemy as sa
import re
from flask_sockets import Sockets
from geventwebsocket.websocket import WebSocket
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from stewdio.search import search_favorites
from stewdio.types.user import UserApiKey

from . import config
from . import library
from . import pubsub
from . import tagging
from . import types
from .misc import json_api, with_pg_cursor, with_db_session, db_session
from .search import search as search_internal, get_random, Context as SearchContext
from .user import api as user_api, find_user_by_api_key, requires_api_key, check_api_key

L = logging.getLogger("stewdio.app")

app = flask.Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.register_blueprint(tagging.api)
app.register_blueprint(user_api)
websocket = Sockets(app)


def kawa(api_function_name):
    return config.kawa_api + api_function_name


@app.before_request
def request_logger():
    L.info("Request: {}".format(flask.request.path))


def requires_api_key_if_user_has_password(fn):
    @wraps(fn)
    def wrapper(*args, username, session, **kwargs):
        db_user = find_user_by_api_key(session, flask.request)
        if not db_user or db_user.name != username.lower():
            db_user = session.query(types.User).filter_by(name=username.lower()).one_or_none()
            if db_user and db_user.password:
                return flask.Response(
                    json.dumps({"error": "authentication required"}),
                    status=403
                )
        return fn(*args, username=username, session=session, **kwargs)

    return wrapper

def getOrderByClause(orderBy, orderDirection):
    if str(orderDirection).lower() == 'desc':
        orderDirection = 'DESC'
    else:
        orderDirection = 'ASC'

    if orderBy == 'albumPath' or orderBy == 'default' or orderBy == '' or orderBy == None:
        return ' ORDER BY album ' + orderDirection + ', path ' + orderDirection + ' '
    elif orderBy == 'score':
        return ' ORDER BY (favorite_count * 5 + play_count + (CASE WHEN path ILIKE \'%.flac\' THEN 5 ELSE 0 END)) ' + orderDirection + ', path ' + orderDirection + ' '
    elif orderBy == 'title':
        return ' ORDER BY title ' + orderDirection + ', path ' + orderDirection + ' '
    elif orderBy == 'favorites':
        return ' ORDER BY favorite_count ' + orderDirection + ', path ' + orderDirection + ' '
    elif orderBy == 'plays':
        return ' ORDER BY play_count ' + orderDirection + ', path ' + orderDirection + ' '
    else:
        return ' ORDER BY album ' + orderDirection + ', path ' + orderDirection + ' '

@app.route("/api/search/<q>")
@with_pg_cursor
@json_api
@check_api_key
def search(q, cur):
    order_by = getOrderByClause(flask.request.args.get('orderBy'), flask.request.args.get('orderDirection'))
    limit = min(5000, max(50, int(flask.request.args.get("limit", 150)))) or None
    with db_session() as session:
        context = get_np_context(session)
    return search_internal(cur, context, q, limit=limit, order_by=order_by)


@app.route("/api/search")
@with_pg_cursor
@json_api
@check_api_key
def search2(cur):
    q = flask.request.args['q']
    order_by = getOrderByClause(flask.request.args.get('orderBy'), flask.request.args.get('orderDirection'))
    limit = min(5000, max(50, int(flask.request.args.get("limit", 150)))) or None
    with db_session() as session:
        context = get_np_context(session)
    return search_internal(cur, context, q, limit=limit, order_by=order_by)


@app.route("/api/random")
@with_pg_cursor
@json_api
@check_api_key
def get_random_song(cur):
    q = flask.request.args.get('q', '')
    return get_random(cur, q, config.off_vocal_regex)


def queue_song(song, source=None):
    L.info("Song {} requested".format(song["hash"]))
    song["source"] = source
    resp = requests.post(kawa('queue/tail'), json=song)
    queue_id = resp.json().get('queue_id')
    pubsub.events.queue(dict(action='add', song=song, queue_id=queue_id))
    pubsub.basic.queue(dict(action='add', song=song.copy(), queue_id=queue_id))
    return song


@app.route("/api/request/<hash>")
@with_db_session
@requires_api_key
@json_api
def request(user, hash, session):
    song = session.query(types.Song).filter(types.Song.hash.startswith(hash)).one()
    return queue_song(song.json(), "@" + user.name)


@app.route("/api/request/favorite/<username>")
@with_db_session
@requires_api_key
@json_api
def request_favorite(user, session, username, num=1):
    username = username.lower()
    if "num" in flask.request.args:
        num = int(flask.request.args["num"])
    user = session.query(types.User).filter_by(name=username).one_or_none()
    if not user:
        return None, 404
    favs = (session.query(types.Song)
            .filter(types.Song.favored_by.contains(user))
            .order_by(sa.func.random())
            .limit(num).all())
    ret = [queue_song(song.json(), "@" + user.name) for song in favs]
    return ret


@app.route("/api/request/random/<terms>")
@with_pg_cursor
@with_db_session
@requires_api_key
@json_api
def request_random(user, session, terms, cur):
    context = get_np_context(session)
    songs = search_internal(cur, context, terms)
    old_queue = _get_queue()
    for song in songs[:]:
        for s in old_queue:
            if s.get('id') == song.get('id'):
                songs.remove(song)
                break
    if not songs:
        return flask.Response(status=404)
    song = random.choice(songs)
    return queue_song(song, "@" + user.name)


@app.route("/api/request/random")
@with_pg_cursor
@with_db_session
@requires_api_key
@json_api
def request_random2(user, session, cur):
    q = flask.request.args['q']
    context = get_np_context(session)
    songs = search_internal(cur, context, q)
    old_queue = _get_queue()
    for song in songs[:]:
        for s in old_queue:
            if s.get('id') == song.get('id'):
                songs.remove(song)
                break
    if not songs:
        return flask.Response(status=404)
    song = random.choice(songs)
    return queue_song(song, "@" + user.name)


@app.route("/api/skip")
@with_db_session
@requires_api_key
def skip(user, session):
    if _listeners(session)["num_listeners"] <= 2:
        song = requests.post(kawa('skip')).json()
        song["source"] = "@" + user.name
        queue_id = song.get('queue_id')
        pubsub.events.queue(dict(action='remove', song=song, queue_id=queue_id))
        pubsub.basic.queue(dict(action='remove', song=song.copy(), queue_id=queue_id))
    return ""


@app.route("/api/queue/head", methods=['DELETE'])
@with_db_session
@requires_api_key
def queue_remove_head(user, session):
    old_queue = _get_queue()
    song = requests.delete(kawa('queue/head')).json()
    song = old_queue.pop(0)
    song["source"] = "@" + user.name;
    queue_id = song.get('queue_id')
    pubsub.events.queue(dict(action='remove', song=song, queue_id=queue_id))
    pubsub.basic.queue(dict(action='remove', song=song.copy(), queue_id=queue_id))
    return ""


@app.route("/api/queue/tail", methods=['DELETE'])
@with_db_session
@requires_api_key
def queue_remove_tail(user, session):
    old_queue = _get_queue()
    song = requests.delete(kawa('queue/tail')).json()
    song = old_queue.pop()
    song["source"] = "@" + user.name;
    queue_id = song.get('queue_id')
    pubsub.events.queue(dict(action='remove', song=song, queue_id=queue_id))
    pubsub.basic.queue(dict(action='remove', song=song.copy(), queue_id=queue_id))
    return ""


@app.route("/api/download/<hash>")
@with_db_session
def download(hash, session):
    song = session.query(types.Song).filter(types.Song.hash.startswith(hash)).one_or_none()
    if not song:
        return flask.Response(status=404)
    path = song.path
    db_user = find_user_by_api_key(session, flask.request)
    if not db_user:
        rate_limit = str(int(max(os.path.getsize(path) / song.duration + 100000, 300000)))
    else:
        rate_limit = "off"

    try:
        os.path.basename(path).encode('ascii')
        file_expr = 'filename="{}"'.format(os.path.basename(path))
    except UnicodeEncodeError:
        # Handle a non-ASCII filename
        file_expr = "filename*=utf-8''{}".format(quote(os.path.basename(path)))
    if not os.path.exists(path.encode('utf-8')):
        return flask.Response(status=404)
    return flask.Response(status=206, direct_passthrough=True,
                          headers={'Content-Type': '', 'X-Accel-Redirect': quote(path.encode('utf-8')),
                                   'X-Accel-Limit-Rate': rate_limit, 'Accept-Ranges': 'bytes',
                                   'X-Accel-Buffering': 'no', 'Content-Transfer-Encoding': 'binary',
                                   'Content-Disposition': 'inline; {}'.format(file_expr)})


def _get_listener_header(listener, h):
    for header in listener["headers"]:
        if header["name"].lower() == h:
            return header["value"]
    return None


def _listeners(session):
    r = requests.get(kawa('listeners'))
    named_listeners = []
    num_listeners = 0
    for listener in r.json():
        path_split = urlsplit(listener["path"])
        q = parse_qs(path_split.query)
        key = None
        auth = _get_listener_header(listener, "authorization")
        c = cookies.SimpleCookie()
        cookie = _get_listener_header(listener, "cookie")
        if cookie:
            c.load(cookie)

        if not key and "apikey" in q:
            key = q.get("apikey")[0]
        if not key and "radio-apikey" in c:
            key = c["radio-apikey"].value
        if not key and auth:
            key = auth
        if not key and "user" in q:
            key = q.get("user")[0]
        if key:
            key = session.query(UserApiKey).filter_by(key=unquote(key)).one_or_none()
            if key and key.user:
                named_listeners.append(key.user.name)
        num_listeners += 1

    return {
        "num_listeners": num_listeners,
        "named_listeners": named_listeners,
    }


@app.route("/api/listeners")
@json_api
@with_db_session
@check_api_key
def listeners(session):
    return _listeners(session)


@with_db_session
def listeners_updater(session):
    listeners_data = None
    while True:
        old_data = listeners_data
        try:
            listeners_data = _listeners(session)
        except:
            L.exception("Exception while updating listener data")
        if listeners_data != old_data:
            pubsub.events.listeners(listeners_data)
            pubsub.basic.listeners(listeners_data.copy())
        gevent.sleep(1)


gevent.spawn(listeners_updater)


@app.route("/api/playing")
@with_db_session
@check_api_key
@json_api
def playing(session):
    return get_np_json(session)


@app.route("/api/favorites/<username>")
@with_pg_cursor
@json_api
@check_api_key
def favorites(username, cur):
    order_by = getOrderByClause(flask.request.args.get('orderBy'), flask.request.args.get('orderDirection'))
    username = username.lower()
    return search_favorites(cur, username, order_by=order_by)


@app.route("/api/favorites/<username>/<hash>", methods=["GET"])
@json_api
@check_api_key
def check_favorite(username, hash, session):
    username = username.lower()
    if hash == "playing":
        song = get_np_song(session)
        if not song:
            return flask.Response(status=500)
    else:
        int(hash, 16)  # validate hex
        song = session.query(types.Song).filter(types.Song.hash.startswith(hash)).one()
    username = session.query(types.User).filter_by(name=username).one_or_none()
    fav = username and username in song.favored_by
    return {"favorite": fav}


@app.route("/api/favorites/<username>/<hash>", methods=["PUT"])
@with_db_session
@requires_api_key_if_user_has_password
def add_favorite(username, hash, session):
    username = username.lower()
    if hash == "playing":
        song = get_np_song(session)
        if not song:
            return flask.Response(status=500)
    else:
        int(hash, 16)  # validate hex
        song = session.query(types.Song).filter(types.Song.hash.startswith(hash)).one()
    user = session.query(types.User).filter_by(name=username).one_or_none()
    if not user:
        user = types.User(name=username)
        session.add(user)
    was_faved = user in song.favored_by
    song.favored_by.add(user)
    pubsub.events.favorite(dict(action='add', song=song.json(), user=user.name))
    return flask.Response(status=200 if was_faved else 201)


@app.route("/api/favorites/<username>/<hash>", methods=["DELETE"])
@with_db_session
@requires_api_key_if_user_has_password
def remove_favorite(username, hash, session):
    username = username.lower()
    if hash == "playing":
        song = get_np_song(session)
        if not song:
            return flask.Response(status=500)
    else:
        int(hash, 16)  # validate hex
        song = session.query(types.Song).filter(types.Song.hash.startswith(hash)).one()
    user = session.query(types.User).filter_by(name=username).one_or_none()
    if not user:
        return flask.Response(status=404)
    song.favored_by.discard(user)
    pubsub.events.favorite(dict(action='remove', song=song.json(), user=user.name))
    return flask.Response(status=200)


@with_db_session
def _get_queue(session):
    fixed_queue = []
    queue = requests.get(kawa('queue')).json()
    for index, song in enumerate(queue):
        fixed_queue.append(session.query(types.Song).filter(types.Song.id == song["id"]).one().json())
    return fixed_queue


@app.route("/api/queue")
@json_api
@check_api_key
def get_queue():
    return _get_queue()


@app.route("/api/history")
@with_db_session
@check_api_key
@json_api
def history(session):
    n = min(int(flask.request.args.get('n', 50)), 100)
    q = (session.query(types.History)
         .order_by(types.History.play_time.desc())
         .limit(n))
    return [h.json() for h in q]


@app.route("/api/info/<hash>/lyrics/<lyric>")
@with_db_session
@check_api_key
@json_api
def info_lyrics(hash, lyric, session):
    song = session.query(types.Song).filter(types.Song.hash.startswith(hash)).one_or_none()
    if not song or not song.lyrics or lyric not in dict(song.lyrics):
        return flask.Response(status=404)
    return dict(song.lyrics).get(lyric)

@app.route("/api/info/<hash>")
@with_db_session
@check_api_key
@json_api
def info(hash, session):
    song = session.query(types.Song).filter(types.Song.hash.startswith(hash)).one_or_none()
    if not song:
        return flask.Response(status=404)
    return song.json()


@app.route("/api/cover/<id>")
@app.route("/api/cover/<id>/original")
@with_db_session
@json_api
def cover(id, session):
    cover = session.query(types.Cover).filter(types.Cover.id == id).one_or_none()
    if not cover:
        return flask.Response(status=404)
    return flask.Response(status=200, response=cover.data, mimetype=cover.mime)


@app.route("/api/cover/<id>/small")
@with_db_session
@json_api
def cover_thumb_small(id, session):
    cover = session.query(types.Cover).filter(types.Cover.id == id).one_or_none()
    if not cover:
        return flask.Response(status=404)
    data = None
    mime = None
    if cover.thumb_small:
        data = cover.thumb_small
        mime = "image/jpeg"
    if not data and cover.thumb_large:
        data = cover.thumb_large
        mime = "image/jpeg"
    if not data:
        data = cover.data
        mime = cover.mime

    return flask.Response(status=200, response=data, mimetype=mime)


@app.route("/api/cover/<id>/large")
@with_db_session
@json_api
def cover_thumb_large(id, session):
    cover = session.query(types.Cover).filter(types.Cover.id == id).one_or_none()
    if not cover:
        return flask.Response(status=404)
    data = None
    mime = None
    if cover.thumb_large:
        data = cover.thumb_large
        mime = "image/jpeg"
    if not data:
        data = cover.data
        mime = cover.mime

    return flask.Response(status=200, response=data, mimetype=mime)


@app.route("/api/status")
@with_db_session
@check_api_key
@json_api
def status(session):
    database = False
    try:
        res = session.connection().execute('SELECT 1;')
        database = res.cursor.fetchone()[0] == 1
    except Exception as e:
        L.exception("Database check failed")

    kawa_status = False
    try:
        kawa_status = 'id' in requests.get(kawa('np')).json()
    except Exception as e:
        L.exception("Kawa check failed")

    storage = {}
    for name, path in config.storage_status.items():
        storage[name] = os.path.exists(path)

    return dict(
        database=database,
        kawa=kawa_status,
        storage=storage)


@websocket.route("/api/events/basic")
def ws_connect(ws: WebSocket):
    with db_session() as s:
        np = get_np_json(s)
        ws.send(json.dumps(dict(type='playing', data=pubsub.clear_secret_data(np))))
        ws.send(json.dumps(dict(type='listeners', data=pubsub.clear_secret_data(_listeners(s)))))
        queue = _get_queue()
        for index, song in enumerate(queue):
            queue[index] = pubsub.clear_secret_data(song)
        ws.send(json.dumps(dict(type='queue', data=dict(action="initial", queue=queue))))
    pubsub.basic.register_client(ws)


@websocket.route("/api/events/all")
@check_api_key
def ws_connect(ws: WebSocket):
    with db_session() as s:
        np = get_np_json(s)
        ws.send(json.dumps(dict(type='playing', data=np)))
        ws.send(json.dumps(dict(type='listeners', data=_listeners(s))))
        ws.send(json.dumps(dict(type='queue', data=dict(action="initial", queue=_get_queue()))))
    pubsub.events.register_client(ws)


def get_np_song(session):
    hist = (session.query(types.History)
            .order_by(types.History.id.desc())
            .limit(1)
            .one_or_none())
    return hist.song


def get_np_json(session):
    hist = (session.query(types.History)
            .order_by(types.History.id.desc())
            .limit(1)
            .one_or_none())
    np = hist.song.json()
    np['started'] = hist.play_time.timestamp()
    return np


def get_np_context(session):
    song = get_np_song(session)
    return SearchContext(
        artist=song.artist.name,
        album=song.album.name,
        audio=song.audio_hash,
    )


@app.route("/admin/library/update", methods=["POST"])
@with_db_session
@json_api
def update_index(session):
    return [song.json() for song in library.update(session, flask.request.args.get("path"))]


@app.route("/admin/library/unlist", methods=["POST"])
@with_db_session
@json_api
def unlist(session):
    hash = flask.request.args.get("hash")
    try:
        s = session.query(types.Song).filter(types.Song.hash.startswith(hash)).one()
        s.status = types.SongStatus.unlisted
        return s.json()
    except MultipleResultsFound as e:
        return {"error": "multiple matches"}, 400
    except NoResultFound as e:
        return {"error": "no matches"}, 400


@app.route("/admin/playing", methods=["POST"])
@with_db_session
def update_playing(session):
    np = flask.request.get_json(force=True)
    queue_id = np.get('queue_id')
    source = None
    if 'source' in np:
        source = np["source"]
    if 'id' in np:
        hist = types.History(song_id=np["id"], source=source)
        session.add(hist)
        session.flush()
        np = hist.song.json()
    np['started'] = datetime.utcnow().timestamp()
    pubsub.events.queue(dict(action='remove', song=np, queue_id=queue_id))
    pubsub.events.playing(np)
    pubsub.basic.queue(dict(action='remove', song=np.copy(), queue_id=queue_id))
    pubsub.basic.playing(np.copy())
    return ""


@app.route("/admin/push", methods=["POST"])
@with_db_session
def update_push(session):
    type = flask.request.values.get("type")
    data = json.loads(flask.request.values.get("data"))
    if hasattr(pubsub.events, type):
        getattr(pubsub.events, type)(data)
    if hasattr(pubsub.basic, type):
        getattr(pubsub.basic, type)(data.copy())
    return ""
