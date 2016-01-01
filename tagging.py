import psycopg2
import psycopg2.extras
import logging

from misc import with_pg_cursor, json_api, song_hash2id
from update import update

from flask import Blueprint


L = logging.getLogger("stewdio.tagging")

api = Blueprint("tagging", "tagging", url_prefix="/api/tag")

@api.route("/<song_id>/add/<tag>", methods=["POST"])
@with_pg_cursor(cursor_factory=psycopg2.extras.DictCursor)
@song_hash2id("song_id")
@json_api
def add(cur, song_id, tag):
	cur.execute("SELECT id FROM tags WHERE name = %s", (tag,))
	res = cur.fetchone()
	if not res:
		cur.execute("INSERT INTO tags (name) VALUES (%s) RETURNING id", (tag,))
		res = cur.fetchone()

	try:
		cur.execute("INSERT INTO taggings (song, tag) VALUES (%s, %s)", (song_id, res[0]))
	except psycopg2.IntegrityError:
		return {"created": False}, 200
	update(limit_ids=(song_id,), cur=cur)
	return {"created": True}, 201

@api.route("/<song_id>/remove/<tag>", methods=["POST"])
@with_pg_cursor()
@song_hash2id("song_id")
@json_api
def remove(cur, song_id, tag):
	cur.execute("SELECT id FROM tags WHERE name = %s", (tag,))
	res = cur.fetchone()
	if not res:
		return {"error": "tag does not exist"}, 404
	cur.execute("DELETE FROM taggings WHERE song = %s AND tag = %s", (song_id, res[0]))
	if cur.rowcount == 0:
		return {"removed": False}, 200
	update(limit_ids=(song_id,))
	return {"removed": True}, 201
