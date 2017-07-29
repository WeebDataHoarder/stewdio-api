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
from urllib.parse import urlsplit, parse_qs
import psycopg2.extras
import eventlet
import requests
import random
from functools import reduce
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

@app.route("/api/random")
@with_pg_cursor(cursor_factory=psycopg2.extras.DictCursor)
@json_api
def get_random_song(cur):
	res = None
	while not res:
		cur.execute("""
				SELECT songs.id AS id, location AS path FROM songs
				WHERE status='active'
				OFFSET random() * (SELECT COUNT(*) FROM songs) LIMIT 1""")
		res = cur.fetchone()
	return {"id": res["id"], "path": res["path"]}

def queue_song(song):
		L.info("Song {} requested".format(song["hash"]))
		requests.post(kawa('queue/tail'), json={"id": int(song["id"]), "path": song["path"]})
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
def download(hash):
	with ix.searcher() as searcher:
		res = searcher.search(Prefix("hash", hash), limit=1)
		if len(res) == 0:
			return flask.Response(status=404)
		path = res[0]["path"]
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
	req = requests.get(kawa('queue'))
	queued_songs = [x["id"] for x in req.json()]
	if not queued_songs:
		return []
	song_infos = {s["id"]: s for s in get_song_info(queued_songs)}
	return [song_infos[id] for id in queued_songs]

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

@app.route("/admin/playing", methods=["POST"])
def update_playing():
	np = flask.request.get_json()
	info = get_song_info([np['id']])[0]
	redis.set("np_data", json.dumps(info))
	redis.publish("playing", json.dumps(info))
	redis.zadd("history", time.time(), json.dumps(info))
	return ""

if __name__ == '__main__':
	app.debug = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "on")
	socketio.run(app)
