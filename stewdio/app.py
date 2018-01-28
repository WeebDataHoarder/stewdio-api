import json
import logging
import os
import random
from urllib.parse import urlsplit, parse_qs

import flask
import gevent
import psycopg2.extras
import requests
from flask_sockets import Sockets
from geventwebsocket.websocket import WebSocket

from . import config
from . import tagging
from .misc import json_api, with_pg_cursor
from . import pubsub
from .search import search as search_internal, search_by_hash, search_favorites, get_random

L = logging.getLogger("stewdio.app")

app = flask.Flask(__name__)
app.register_blueprint(tagging.api)
websocket = Sockets(app)

def kawa(api_function_name):
	return config.kawa_api + api_function_name

@app.route("/")
def index():
	return flask.render_template("index.html")

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
	requests.post(kawa('queue/tail'), json=song)
	pubsub.events.queue(dict(action='add', song=song))
	return song

@app.route("/api/request/<hash>")
@with_pg_cursor
@json_api
def request(hash, cur):
	song = search_by_hash(cur, hash)
	return queue_song(song)

@app.route("/api/request/favorite/<user>")
@with_pg_cursor
@json_api
def request_favorite(cur, user, num=1):
	if "num" in flask.request.args:
		num = int(flask.request.args["num"])
	favs = search_favorites(cur, user)
	random.shuffle(favs)
	favs = favs[:num]
	ret = [queue_song(song) for song in favs]
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
	pubsub.events.queue(dict(action='remove', song=song))
	return ""

@app.route("/api/queue/head", methods=['DELETE'])
def queue_remove_head():
	song = requests.delete(kawa('queue/head')).json()
	pubsub.events.queue(dict(action='remove', song=song))
	return ""

@app.route("/api/queue/tail", methods=['DELETE'])
def queue_remove_tail():
	song = requests.delete(kawa('queue/tail')).json()
	pubsub.events.queue(dict(action='remove', song=song))
	return ""

@app.route("/api/download/<hash>")
@with_pg_cursor
def download(hash, cur):
	song = search_by_hash(cur, hash)
	if not song:
		return flask.Response(status=404)
	path = song["path"]
	att_fn = os.path.basename(path).encode('ascii', errors='replace').decode('ascii').replace('?', '_')
	if not os.path.exists(path):
		return flask.Response(status=404)
	return flask.send_file(path, as_attachment=True, attachment_filename=att_fn)

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
@json_api
def playing():
	return np

@app.route("/api/favorites/<user>")
@with_pg_cursor
@json_api
def favorites(user, cur):
	return search_favorites(cur, user)

@app.route("/api/favorites/<user>/<hash>", methods=["GET"])
@json_api
@with_pg_cursor
def check_favorite(user, hash, cur=None):
	if hash == "playing":
		song = np
		if not song:
			return flask.Response(status=500)
	else:
		int(hash, 16)  # validate hex
		song = search_by_hash(cur, hash)
	song_id = song['id']
	cur.execute("SELECT id FROM users WHERE nick = %s", (user.lower(),))
	user_id = cur.fetchone()
	if not user_id:
		return {"favorite": False}
	cur.execute("""SELECT COUNT(*) FROM favorites WHERE
		account = %s AND song = %s""", (user_id[0], song_id))
	return {"favorite": cur.fetchone()[0] > 0}

@app.route("/api/favorites/<user>/<hash>", methods=["PUT"])
@with_pg_cursor
def add_favorite(user, hash, cur=None):
	if hash == "playing":
		song = np
		if not song:
			return flask.Response(status=500)
	else:
		int(hash, 16)  # validate hex
		song = search_by_hash(cur, hash)
	song_id = song['id']
	cur.execute("SELECT id FROM users WHERE nick = %s", (user.lower(),))
	user_id = cur.fetchone()
	if not user_id:
		cur.execute("INSERT INTO users (nick) VALUES (%s) RETURNING id", (user.lower(),))
		user_id = cur.fetchone()
	try:
		cur.execute("""INSERT INTO favorites
			(account, song) VALUES (%s, %s)""", (user_id[0], song_id))

		pubsub.events.favorite(dict(action='add', song=song, user=user))
	except psycopg2.IntegrityError as e:
		return flask.Response(status=200)
	else:
		return flask.Response(status=201)

@app.route("/api/favorites/<user>/<hash>", methods=["DELETE"])
@with_pg_cursor
def remove_favorite(user, hash, cur=None):
	if hash == "playing":
		song = np
		if not song:
			return flask.Response(status=500)
	else:
		int(hash, 16)  # validate hex
		song = search_by_hash(cur, hash)
	song_id = song['id']
	cur.execute("SELECT id FROM users WHERE nick = %s", (user.lower(),))
	user_id = cur.fetchone()
	if not user_id:
		return flask.Response(status=400)
	cur.execute("""DELETE FROM favorites
			WHERE account = %s AND song = %s;""", (user_id[0], song_id))

	pubsub.events.favorite(dict(action='remove', song=song, user=user))
	return flask.Response(status=200)

@app.route("/api/queue")
@json_api
def get_queue():
	return requests.get(kawa('queue')).json()

@app.route("/api/info/<hash>")
@with_pg_cursor
@json_api
def info(hash, cur):
	song = search_by_hash(cur, hash)
	if not song:
		return flask.Response(status=404)
	return song

@app.route("/api/status")
@with_pg_cursor
@json_api
def status(cur):
	database = False
	try:
		cur.execute('''SELECT 1;''')
		database = cur.fetchone()[0] == 1
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
	ws.send(json.dumps(np))
	pubsub.playing.register_client(ws)

@websocket.route("/api/events/all")
def ws_connect(ws: WebSocket):
	ws.send(json.dumps(dict(type='playing', data=np)))
	pubsub.events.register_client(ws)

try:
	np = requests.get(kawa('np')).json()
except:
	np = None

@app.route("/admin/playing", methods=["POST"])
@with_pg_cursor
def update_playing(cur):
	global np
	np = flask.request.get_json(force=True)
	cur.execute("""INSERT INTO history (data) VALUES (%s)""", (np,))
	pubsub.playing.publish(np)
	pubsub.events.playing(np)
	return ""
