import psycopg2

from misc import with_cur, json_api
from update import update

from flask import Blueprint


api = Blueprint("tagging", "tagging", url_prefix="/api/tag")

@api.route("/<song_id>/add/<tag>")
@with_cur
@json_api
def add(cur, song_id, tag):
	cur.execute("SELECT id FROM tags WHERE name = %s", (tag,))
	res = cur.fetchone()
	if not res:
		return {"error": "tag does not exist"}, 404
	try:
		cur.execute("INSERT INTO taggings (song, tag) VALUES (%s, %s)", (song_id, res[0]))
	except psycopg2.IntegrityError:
		return {"created": False}, 200
	update(limit_ids=(song_id,))
	return {"created": True}, 201

@api.route("/<song_id>/remove/<tag>")
@with_cur
@json_api
def remove(cur, song_id, tag):
	cur.execute("SELECT id FROM tags WHERE name = %s", (tag,))
	res = cur.fetchone()
	if not res:
		return {"error": "tag does not exist"}, 404
	try:
		cur.execute("DELETE FROM taggings WHERE song = %s AND tag = %s", (song_id, res[0]))
	except psycopg2.IntegrityError:
		return {"removed": False}, 200
	update(limit_ids=(song_id,))
	return {"removed": True}, 201

@api.route("/create/<tag>")
@with_cur
@json_api
def create(cur, tag):
	try:
		cur.execute("INSERT INTO tags (name) VALUES (%s)", (tag,))
	except psycopg2.IntegrityError:
		return {"created": False}, 200
	return {"created": True}, 201
