from schema import ix

import os
import json
from flask import Flask, request
import flask
from whoosh.qparser import MultifieldParser

app = Flask(__name__)


@app.route("/")
def index():
	return flask.render_template("index.html")


@app.route("/search/<q>")
def search(q):
	parser = MultifieldParser(["title", "artist", "album"], ix.schema)
	myquery = parser.parse(q)
	with ix.searcher() as searcher:
		res = searcher.search(myquery, limit=30)
		return flask.Response(
			json.dumps([dict(r) for r in res]),
			mimetype="application/json"
		)


if __name__ == '__main__':
	app.debug = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "on")
	app.run()
