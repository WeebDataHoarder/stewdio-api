from schema import ix
from config import redis
import config
from update import update
import tagging
from misc import json_api

import os
import json
import flask
from flask.ext.socketio import SocketIO, emit
from whoosh.qparser import MultifieldParser, GtLtPlugin, PlusMinusPlugin
from whoosh.query import Prefix
from urllib.parse import urlparse, parse_qs
import eventlet
import requests
import logging

L = logging.getLogger("stewdio.app")

app = flask.Flask(__name__)
app.register_blueprint(tagging.api)
socketio = SocketIO(app)

@app.route("/")
def index():
	return flask.render_template("index.html")


@app.route("/api/search/<q>")
@json_api
def search(q):
	parser = MultifieldParser(["title", "artist"], ix.schema)
	parser.add_plugin(GtLtPlugin())
	parser.add_plugin(PlusMinusPlugin())
	myquery = parser.parse(q)
	L.debug("Search query: {}".format(myquery))
	with ix.searcher() as searcher:
		res = searcher.search(myquery, limit=30)
		return [dict(r) for r in res]

@app.route("/api/request/<hash>")
@json_api
def request(hash):
	with ix.searcher() as searcher:
		res = searcher.search(Prefix("hash", hash), limit=1)
		if len(res) == 0:
			return flask.Response(status=400)
		redis.lpush("queue", json.dumps({"hash": res[0]["hash"]}))
		L.info("Song {} requested".format(res[0]["hash"]))
		return dict(res[0])

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
		"title": data.get("title"),
		"artist": data.get("artist"),
		"album": data.get("album"),
		"hash": data.get("hash"),
	}

@app.route("/api/playing")
@json_api
def playing():
	data = json.loads(redis.get("np_data").decode("utf-8"))
	return format_playing(data)

def playing_publisher():
	L.info("Starting PubSub listener")
	pubsub = redis.pubsub()
	pubsub.subscribe("playing")
	for m in pubsub.listen():
		if m["type"] != "message":
			continue
		L.debug("Emitting now playing info")
		socketio.emit("playing", format_playing(json.loads(redis.get("np_data").decode("utf-8"))))
eventlet.spawn_n(playing_publisher)

@socketio.on("connect")
def ws_connect():
	emit("playing", format_playing(json.loads(redis.get("np_data").decode("utf-8"))))

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
