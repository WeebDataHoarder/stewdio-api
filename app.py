import socket

from schema import ix
from config import redis
import config
from update import update
import tagging
from misc import json_api, with_pg_cursor


import os
import json
import flask
from flask.ext.socketio import SocketIO, emit
from whoosh.qparser import MultifieldParser, GtLtPlugin, PlusMinusPlugin
from whoosh.query import Prefix, Term
from urllib.parse import urlparse, parse_qs
import psycopg2.extras
import eventlet
import requests
import random
from functools import reduce
import logging

L = logging.getLogger("stewdio.app")

app = flask.Flask(__name__)
app.register_blueprint(tagging.api)
socketio = SocketIO(app)

@app.route("/")
def index():
	return flask.render_template("index.html")

def search_internal(q, limit=None):
	parser = MultifieldParser(["title", "artist"], ix.schema)
	parser.add_plugin(GtLtPlugin())
	parser.add_plugin(PlusMinusPlugin())
	myquery = parser.parse(q)
	L.debug("Search query: {}".format(myquery))
	with ix.searcher() as searcher:
		res = searcher.search(myquery, limit=limit)
		return [dict(r) for r in res]

@app.route("/api/search/<q>")
@json_api
def search(q):
	return search_internal(q, limit=int(flask.request.args.get("limit", 0)) or None)

def queue_song(song):
		redis.lpush("queue", json.dumps(song))
		L.info("Song {} requested".format(song["hash"]))
		return dict(song)

@app.route("/api/request/<hash>")
@json_api
def request(hash):
	return request_internal(hash)

def request_internal(hash):
	with ix.searcher() as searcher:
		res = searcher.search(Prefix("hash", hash), limit=1)
		if len(res) == 0:
			return flask.Response(status=404)
		return queue_song(dict(res[0]))

@app.route("/api/request/favorite/<user>")
@with_pg_cursor(cursor_factory=psycopg2.extras.DictCursor)
@json_api
def request_favorite(cur, user, num=1):
	if "num" in flask.request.args:
		num = int(flask.request.args["num"])
	favs = get_favs((user,))[user]
	random.shuffle(favs)
	favs = favs[:num]
	cur.execute("""SELECT hash FROM songs WHERE id IN %s;""", (tuple(favs),))
	ret = [request_internal(song["hash"]) for song in cur]
	return ret

@app.route("/api/request/random/<terms>")
@json_api
def request_random(terms):
	songs = search_internal(terms)
	if not songs:
		return flask.Response(status=404)
	song = random.choice(songs)
	return queue_song(song)

@app.route("/api/skip")
def skip():
	sock = socket.socket()
	sock.connect(config.liquidsoap)
	sock.sendall(b"stream(dot)flac.skip\r\n")
	sock.close()
	return ""

@app.route("/api/download/<hash>")
def download(hash):
	with ix.searcher() as searcher:
		res = searcher.search(Prefix("hash", hash), limit=1)
		if len(res) == 0:
			return flask.Response(status=404)
		return flask.send_file(res[0]["path"], as_attachment=True)

@app.route("/api/listeners")
@json_api
def listeners():
	return {
		"num_listeners": int(redis.get("num_listeners") or 0),
		"named_listeners": [user.decode("utf-8")
			for user in redis.smembers("named_listeners")],
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

@with_pg_cursor()
def get_favs(users, cur=None):
	cur.execute("""
			SELECT u.nick, array_agg(f.song)
			FROM favorites AS f
			JOIN users AS u ON u.id = f.account
			WHERE
				u.nick IN %s
			GROUP BY
				u.id;""",
		(tuple(users),)
	)
	return {row[0]: row[1] for row in cur}

@with_pg_cursor(cursor_factory=psycopg2.extras.DictCursor)
def get_song_info(ids=None, hashes=None, cur=None):
	search_field = "id" if hashes is None else "hash"
	search_values = ids if hashes is None else hashes
	cur.execute("""
			SELECT s.id AS id, s.hash AS hash, s.location AS path,
				s.title AS title, ar.name AS artist, al.name AS album,
				s.length AS duration, s.status AS status,
				array_remove(array_agg(t.name), NULL) AS tags
			FROM  songs AS s
			LEFT JOIN artists AS ar ON s.artist = ar.id
			LEFT JOIN albums AS al ON s.album = al.id
			LEFT JOIN taggings AS ts ON s.id = ts.song
			LEFT JOIN tags AS t ON ts.tag = t.id
			WHERE
				s.{} IN %s
			GROUP BY
				s.id, s.hash, s.location, s.title,
				ar.name, al.name, s.length, s.status;""".format(search_field),
		(tuple(search_values),)
	)
	return [dict(row) for row in cur]

@app.route("/api/favorites/<user>")
@json_api
def favorites(user):
	return [dict(songinfo) for songinfo in get_song_info(get_favs((user,))[user])]

@app.route("/api/common_favorites/<users>")
@json_api
def common_favorites(users):
	songs = iter(get_favs(users.split(",")).values())
	unique_songs = reduce(lambda a, b: a.intersection(b),
			map(set, songs), set(next(songs, ())))
	return get_song_info(unique_songs)

@app.route("/api/unique_favorites/<user>/<others>")
@json_api
def unique_favorites(user, others):
	songs = get_favs((user,))[user]
	others_songs = iter(get_favs(others.split(",")).values())
	unique_songs = reduce(lambda a, b: a.difference(b),
			map(set, others_songs), set(songs))
	return get_song_info(unique_songs)

@app.route("/api/favorites/<user>/<hash>", methods=["GET"])
@json_api
@with_pg_cursor()
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
		account = %s AND song = %s""", (user_id, song_id))
	return {"favorite": cur.fetchone()[0] > 0}

@app.route("/api/favorites/<user>/<hash>", methods=["PUT"])
@with_pg_cursor()
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
			(account, song) VALUES (%s, %s)""", (user_id, song_id))
	except psycopg2.IntegrityError as e:
		return flask.Response(status=200)
	else:
		return flask.Response(status=201)

@app.route("/api/favorites/<user>/<hash>", methods=["DELETE"])
@with_pg_cursor()
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
			WHERE account = %s AND song = %s;""", (user_id, song_id))
	return flask.Response(status=200)

@app.route("/api/queue")
@json_api
def get_queue():
	queued_songs = [json.loads(x.decode("utf-8"))["hash"] for x in redis.lrange("queue", 0, -1)]
	if not queued_songs:
		return []
	song_infos = {s["hash"]: s for s in get_song_info(hashes=queued_songs)}
	return [song_infos[hash] for hash in reversed(queued_songs)]

@app.route("/api/info/<hash>")
@json_api
def info(hash):
	with ix.searcher() as searcher:
		res = searcher.search(Prefix("hash", hash), limit=1)
		if len(res) == 0:
			return flask.Response(status=404)
		return dict(res[0])

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

@app.route("/admin/update_index")
def update_index():
	id = flask.request.args.get("id")
	update(limit_path=flask.request.args.get("path"), limit_ids=(id,) if id else None)
	return ""

def update_listener_count():
	icecast_status = requests.get(config.icecast_json).json()
	num_listeners = sum(source["listeners"] for source in icecast_status["icestats"]["source"])
	redis.set("num_listeners", num_listeners)
	redis.publish("listener", "count:{}".format(num_listeners))

@app.route("/icecast", methods=["POST"])
def icecast_auth():
	action = flask.request.form["action"]
	L.info("Icecast auth action: {}".format(action))
	mount = urlparse(flask.request.form["mount"])
	mount_q = parse_qs(mount.query)
	mount_userlist = mount_q.get("user")
	mount_user = mount_userlist[0] if mount_userlist else None
	if not mount.path.startswith("/stream"):
		# requesting the web interface counts as listener too
		return ""
	if action == "listener_add":
		if mount_user:
			if int(redis.incr("named_listeners:" + mount_user)) > 1:
				redis.publish("listener", "connect:" + mount_user)
			redis.sadd("named_listeners", mount_user)
		eventlet.spawn_after(0.5, update_listener_count)
	if action == "listener_remove":
		if mount_user:
			if int(redis.decr("named_listeners:" + mount_user) or 0) <= 0:
				redis.delete("named_listeners:" + mount_user)
				redis.srem("named_listeners", mount_user)
				redis.publish("listener", "disconnect:" + mount_user)
		eventlet.spawn_after(0.5, update_listener_count)
	return ""


if __name__ == '__main__':
	app.debug = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "on")
	socketio.run(app)
