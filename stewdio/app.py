import json
import logging
import os
import random
from functools import wraps
from urllib.parse import urlsplit, parse_qs

import flask
import gevent
import requests
import sqlalchemy as sa
from flask_sockets import Sockets
from geventwebsocket.websocket import WebSocket
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from stewdio.search import search_favorites

from . import config
from . import library
from . import pubsub
from . import tagging
from . import types
from .misc import json_api, with_pg_cursor, with_db_session, db_session
from .search import search as search_internal, get_random
from .user import api as user_api, find_user_by_api_key

L = logging.getLogger("stewdio.app")

app = flask.Flask(__name__)
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
		if not db_user or db_user.name != username:
			db_user = session.query(types.User).filter_by(name=username.lower()).one_or_none()
			if db_user and db_user.password:
				return flask.Response(
					json.dumps({"error": "authentication required"}),
					status=401,
					headers={'WWW-Authenticate': 'Basic realm="Authentication Required"'}
				)
		return fn(*args, username=username, session=session, **kwargs)

	return wrapper

@app.route("/api/search/<q>")
@with_pg_cursor
@json_api
def search(q, cur):
	return search_internal(cur, q, limit=int(flask.request.args.get("limit", 0)) or None)

@app.route("/api/search")
@with_pg_cursor
@json_api
def search2(cur):
	q = flask.request.args['q']
	return search_internal(cur, q, limit=int(flask.request.args.get("limit", 0)) or None)

@app.route("/api/random")
@with_pg_cursor
@json_api
def get_random_song(cur):
	return get_random(cur, config.off_vocal_regex)

def queue_song(song):
	L.info("Song {} requested".format(song["hash"]))
	resp = requests.post(kawa('queue/tail'), json=song)
	queue_id = resp.json().get('queue_id')
	pubsub.events.queue(dict(action='add', song=song, queue_id=queue_id))
	return song

@app.route("/api/request/<hash>")
@with_db_session
@json_api
def request(hash, session):
	song = session.query(types.Song).filter(types.Song.hash.startswith(hash)).one()
	return queue_song(song.json())

@app.route("/api/request/favorite/<username>")
@with_db_session
@json_api
def request_favorite(session, username, num=1):
	if "num" in flask.request.args:
		num = int(flask.request.args["num"])
	user = session.query(types.User).filter_by(name=username).one_or_none()
	if not user:
		return None, 404
	favs = (session.query(types.Song)
			.filter(types.Song.favored_by.contains(user))
			.order_by(sa.func.random())
			.limit(num).all())
	ret = [queue_song(song.json()) for song in favs]
	return ret

@app.route("/api/request/random/<terms>")
@with_pg_cursor
@json_api
def request_random(terms, cur):
	songs = search_internal(cur, terms)
	if not songs:
		return flask.Response(status=404)
	song = random.choice(songs)
	return queue_song(song)

@app.route("/api/skip")
def skip():
	song = requests.post(kawa('skip')).json()
	queue_id = song.get('queue_id')
	pubsub.events.queue(dict(action='remove', song=song, queue_id=queue_id))
	return ""

@app.route("/api/queue/head", methods=['DELETE'])
def queue_remove_head():
	song = requests.delete(kawa('queue/head')).json()
	queue_id = song.get('queue_id')
	pubsub.events.queue(dict(action='remove', song=song, queue_id=queue_id))
	return ""

@app.route("/api/queue/tail", methods=['DELETE'])
def queue_remove_tail():
	song = requests.delete(kawa('queue/tail')).json()
	queue_id = song.get('queue_id')
	pubsub.events.queue(dict(action='remove', song=song, queue_id=queue_id))
	return ""

@app.route("/api/download/<hash>")
@with_db_session
def download(hash, session):
	song = session.query(types.Song).filter(types.Song.hash.startswith(hash)).one_or_none()
	if not song:
		return flask.Response(status=404)
	att_fn = os.path.basename(song.path).encode('ascii', errors='replace').decode('ascii').replace('?', '_')
	if not os.path.exists(song.path):
		return flask.Response(status=404)
	return flask.send_file(song.path, as_attachment=True, attachment_filename=att_fn)

def _listeners():
	r = requests.get(kawa('listeners'))
	named_listeners = []
	num_listeners = 0
	for listener in r.json():
		path_split = urlsplit(listener["path"])
		q = parse_qs(path_split.query)
		if "user" in q:
			named_listeners.append(q["user"][0])
		num_listeners += 1

	return {
		"num_listeners": num_listeners,
		"named_listeners": named_listeners,
	}

@app.route("/api/listeners")
@json_api
def listeners():
	return _listeners()

def listeners_updater():
	listeners_data = None
	while True:
		old_data = listeners_data
		try:
			listeners_data = _listeners()
		except:
			L.exception("Exception while updating listener data")
		if listeners_data != old_data:
			pubsub.events.listeners(listeners_data)
		gevent.sleep(1)

gevent.spawn(listeners_updater)

@app.route("/api/playing")
@with_db_session
@json_api
def playing(session):
	return get_np_json(session)

@app.route("/api/favorites/<username>")
@with_pg_cursor
@json_api
def favorites(username, cur):
	return search_favorites(cur, username)

@app.route("/api/favorites/<username>/<hash>", methods=["GET"])
@json_api
@with_db_session
def check_favorite(username, hash, session):
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

def _get_queue():
	return requests.get(kawa('queue')).json()

@app.route("/api/queue")
@json_api
def get_queue():
	return _get_queue()

@app.route("/api/history")
@with_db_session
@json_api
def history(session):
	n = min(int(flask.request.args.get('n', 10)), 100)
	q = (session.query(types.History)
		.order_by(types.History.play_time.desc())
		.limit(n))
	return [h.json() for h in q]

@app.route("/api/info/<hash>")
@with_db_session
@json_api
def info(hash, session):
	song = session.query(types.Song).filter(types.Song.hash.startswith(hash)).one_or_none()
	if not song:
		return flask.Response(status=404)
	return song.json()

@app.route("/api/status")
@with_db_session
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

@websocket.route("/api/events/playing")
def ws_connect(ws: WebSocket):
	with db_session() as s:
		np = get_np_json(s)
	ws.send(json.dumps(np))
	pubsub.playing.register_client(ws)

@websocket.route("/api/events/all")
def ws_connect(ws: WebSocket):
	with db_session() as s:
		np = get_np_json(s)
	ws.send(json.dumps(dict(type='playing', data=np)))
	ws.send(json.dumps(dict(type='listeners', data=_listeners())))
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
		s.stats = types.SongStatus.unlisted
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
	hist = types.History(song_id=np["id"])
	session.add(hist)
	session.flush()
	np = hist.song.json()
	pubsub.events.queue(dict(action='remove', song=np, queue_id=queue_id))
	np['started'] = hist.play_time.timestamp()
	pubsub.playing.publish(np)
	pubsub.events.playing(np)
	return ""
