from schema import ix
import config
from update import update
import tagging
from misc import json_api

import os
import json
from flask import Flask
import flask
from whoosh.qparser import MultifieldParser, GtLtPlugin, PlusMinusPlugin
from whoosh.query import Prefix
from redis import StrictRedis
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)
app.register_blueprint(tagging.api)
redis = StrictRedis(**config.redis)

@app.route("/")
def index():
	return flask.render_template("index.html")


@app.route("/api/search/<q>")
@json_api
def search(q):
	parser = MultifieldParser(["title", "artist", "album"], ix.schema)
	parser.add_plugin(GtLtPlugin())
	parser.add_plugin(PlusMinusPlugin())
	myquery = parser.parse(q)
	print(myquery)
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

@app.route("/admin/update_index")
def update_index():
	id = flask.request.args.get("id")
	update(limit_path=flask.request.args.get("path"), limit_ids=(id,) if id else None)
	return ""

@app.route("/icecast", methods=["POST"])
def icecast_auth():
	action = flask.request.form["action"]
	mount = urlparse(flask.request.form["mount"])
	mount_q = parse_qs(mount.query)
	mount_userlist = mount_q.get("user")
	mount_user = mount_userlist[0] if mount_userlist else None
	if action == "listener_add":
		if mount_user:
			redis.sadd("named_listeners", mount_user)
		redis.incr("num_listeners")
	if action == "listener_remove":
		if mount_user:
			redis.srem("named_listeners", mount_user)
		redis.decr("num_listeners")
	return ""


if __name__ == '__main__':
	app.debug = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "on")
	app.run()
