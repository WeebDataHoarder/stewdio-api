from schema import ix
import config

import os
import json
from flask import Flask
import flask
from whoosh.qparser import MultifieldParser
from whoosh.query import Prefix
from redis import StrictRedis

app = Flask(__name__)
redis = StrictRedis(**config.redis)

@app.route("/")
def index():
	return flask.render_template("index.html")


@app.route("/api/search/<q>")
def search(q):
	parser = MultifieldParser(["title", "artist", "album"], ix.schema)
	myquery = parser.parse(q)
	print(myquery)
	with ix.searcher() as searcher:
		res = searcher.search(myquery, limit=30)
		return flask.Response(
			json.dumps([dict(r) for r in res]),
			mimetype="application/json"
		)

@app.route("/api/request/<hash>")
def request(hash):
	with ix.searcher() as searcher:
		res = searcher.search(Prefix("hash", hash), limit=1)
		if len(res) == 0:
			return flask.Response(status=400)
		resp = json.dumps(dict(res[0]))
		redis.lpush("queue", json.dumps({"hash": res[0]["hash"]}))
		return resp


if __name__ == '__main__':
	app.debug = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "on")
	app.run()
