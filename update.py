#!/usr/bin/env python3
import config
from misc import with_pg_cursor
from schema import ix

import sys
import psycopg2
import psycopg2.extras
import logging

L = logging.getLogger("stewdio.searchindex")

step_size = 1000

@with_pg_cursor(cursor_factory=psycopg2.extras.DictCursor)
def update(cur, limit_path=None, limit_ids=None):
	L.debug("Updating index with filters: path={} ids={}".format(limit_path, limit_ids))
	with ix.writer() as writer:
		extra_args = []
		extra_query = ""
		if limit_path:
			limit_path = limit_path.replace("%", "\\%").replace("_", "\\_") + "%"
			extra_query += " AND s.location LIKE %s"
			extra_args.append(limit_path)
		if limit_ids:
			extra_query += " AND s.id IN %s"
			extra_args.append(limit_ids)

		cur.execute("""
			SELECT s.id AS id, s.hash AS hash, s.location AS path,
				s.title AS title, ar.name AS artist, al.name AS album,
				s.length AS duration, s.status AS status,
				coalesce(string_agg(t.name, ','), '') AS tags
			FROM songs AS s
			LEFT OUTER JOIN artists AS ar ON s.artist = ar.id
			LEFT OUTER JOIN albums AS al ON s.album = al.id
			LEFT OUTER JOIN taggings AS ts ON s.id = ts.song
			LEFT OUTER JOIN tags AS t ON ts.tag = t.id
			WHERE
				s.status IN ('active') {}
			GROUP BY
				s.id, s.hash, s.location, s.title, ar.name, al.name, s.length, s.status;""".format(extra_query),
			extra_args
		)
		rows = []
		for row in cur:
			rows.append({k: str(v) for k, v in row.items()})
		L.info("Updating songs: {}".format(", ".join(row["id"] for row in rows)))
		for row in rows:
			L.debug("Updating song {}: {}".format(row["id"], row))
			writer.update_document(**row)

if __name__ == "__main__":
	limit_path = None
	limit_ids = []

	if len(sys.argv) > 1:
		try:
			limit_ids = (int(sys.argv[1]),)
		except ValueError:
			limit_path = sys.argv[1]

	update(limit_path=limit_path, limit_ids=limit_ids)
