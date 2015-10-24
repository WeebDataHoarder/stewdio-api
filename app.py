import os
import sys

from schema import ix

import json
from flask import Flask, request
import flask
from whoosh.qparser import QueryParser

app = Flask(__name__)


@app.route("/")
def index():
	return flask.render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
	parser = QueryParser("title", ix.schema)
	myquery = parser.parse(request.form["q"])

	with ix.searcher() as searcher:
		res = searcher.search(myquery)
		print(len(res))
		for r in res:
			print(r)
		return json.dumps(res)


if __name__ == '__main__':
	app.debug = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "on")
	app.run()
