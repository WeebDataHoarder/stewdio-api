from .config import redis
from . import config
from . import tagging
from .misc import json_api, with_pg_cursor
from .search import search as search_internal, search_by_hash, search_favorites, get_random

import os
import json
import flask
from flask_socketio import SocketIO, emit
from urllib.parse import urlsplit, parse_qs
import psycopg2.extras
import eventlet
import requests
import random
import time
import logging

L = logging.getLogger("stewdio.app")

app = flask.Flask(__name__)
app.register_blueprint(tagging.api)
socketio = SocketIO(app)

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

@app.route("/api/random")
@with_pg_cursor
@json_api
def get_random_song(cur):
	return get_random(cur)

def queue_song(song):
		L.info("Song {} requested".format(song["hash"]))
		requests.post(kawa('queue/tail'), json=song)
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
	requests.post(kawa('skip'))
	return ""

@app.route("/api/queue/head", methods=['DELETE'])
def queue_remove_head():
	requests.delete(kawa('queue/head'))
	return ""

@app.route("/api/queue/tail", methods=['DELETE'])
def queue_remove_tail():
	requests.delete(kawa('queue/tail'))
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

@app.route("/api/listeners")
@json_api
def listeners():
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

def format_playing(data):
	return {
		"id": data.get("id"),
		"title": data.get("title"),
		"artist": data.get("artist"),
		"album": data.get("album"),
		"hash": data.get("hash"),
	}

@app.route("/api/playing")
@json_api
def playing():
	data = json.loads(redis.get("np_data").decode("utf-8"))
	return data

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
		data = json.loads(redis.get("np_data").decode("utf-8"))
		hash = data["hash"]
	else:
		int(hash, 16)  # validate hex
	hash += "%"
	cur.execute("SELECT id FROM songs WHERE hash ILIKE %s", (hash,))
	song_id = cur.fetchone()
	cur.execute("SELECT id FROM users WHERE nick = %s", (user,))
	user_id = cur.fetchone()
	if not user_id:
		return {"favorite": False}
	cur.execute("""SELECT COUNT(*) FROM favorites WHERE
		account = %s AND song = %s""", (user_id[0], song_id[0]))
	return {"favorite": cur.fetchone()[0] > 0}

@app.route("/api/favorites/<user>/<hash>", methods=["PUT"])
@with_pg_cursor
def add_favorite(user, hash, cur=None):
	if hash == "playing":
		data = json.loads(redis.get("np_data").decode("utf-8"))
		hash = data["hash"]
	else:
		int(hash, 16)  # validate hex
	hash += "%"
	cur.execute("SELECT id FROM songs WHERE hash ILIKE %s", (hash,))
	song_id = cur.fetchone()
	cur.execute("SELECT id FROM users WHERE nick = %s", (user,))
	user_id = cur.fetchone()
	if not user_id:
		cur.execute("INSERT INTO users (nick) VALUES (%s) RETURNING id", (user,))
		user_id = cur.fetchone()
	try:
		cur.execute("""INSERT INTO favorites
			(account, song) VALUES (%s, %s)""", (user_id[0], song_id[0]))
	except psycopg2.IntegrityError as e:
		return flask.Response(status=200)
	else:
		return flask.Response(status=201)

@app.route("/api/favorites/<user>/<hash>", methods=["DELETE"])
@with_pg_cursor
def remove_favorite(user, hash, cur=None):
	if hash == "playing":
		data = json.loads(redis.get("np_data").decode("utf-8"))
		hash = data["hash"]
	else:
		int(hash, 16)  # validate hex
	hash += "%"
	cur.execute("SELECT id FROM songs WHERE hash ILIKE %s", (hash,))
	song_id = cur.fetchone()
	cur.execute("SELECT id FROM users WHERE nick = %s", (user,))
	user_id = cur.fetchone()
	if not user_id:
		return flask.Response(status=400)
	cur.execute("""DELETE FROM favorites
			WHERE account = %s AND song = %s;""", (user_id[0], song_id[0]))
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

def playing_publisher():
	L.info("Starting PubSub listener")
	pubsub = redis.pubsub()
	pubsub.subscribe("playing")
	for m in pubsub.listen():
		if m["type"] != "message":
			continue
		L.debug("Emitting now playing info")
		socketio.emit("playing", redis.get("np_data").decode("utf-8"))
eventlet.spawn_n(playing_publisher)

@socketio.on("connect")
def ws_connect():
	emit("playing", redis.get("np_data").decode("utf-8"))

@app.route("/admin/playing", methods=["POST"])
def update_playing():
	np = flask.request.get_json()
	redis.set("np_data", json.dumps(np))
	redis.publish("playing", json.dumps(np))
	redis.zadd("history", time.time(), json.dumps(np))
	return ""

if __name__ == '__main__':
	app.debug = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "on")
	socketio.run(app)
