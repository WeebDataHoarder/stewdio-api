#!/usr/bin/env python3
import config
from schema import ix

import sys
import psycopg2
import psycopg2.extras

step_size = 1000

def update(limit_path=None):
	with psycopg2.connect(**config.postgres) as conn:
		with ix.writer() as writer:
			with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
				extra_query = "AND s.location LIKE %s" if limit_path else ""
				cur.execute("""
					SELECT s.id AS id, s.hash AS hash, s.location AS path,
						s.title AS title, ar.name AS artist, al.name AS album,
						s.length AS duration, s.status AS status
					FROM songs AS s
					LEFT OUTER JOIN artists AS ar ON s.artist = ar.id
					LEFT OUTER JOIN albums AS al ON s.album = al.id
					WHERE
						s.status IN ('active', 'unlisted') {};""".format(extra_query),
					(limit_path,)
				)
				for row in cur:
					row = {k: str(v) for k, v in row.items()}
					writer.update_document(**row)

if __name__ == "__main__":
	limit_path = None

	if len(sys.argv) > 1:
		limit_path = sys.argv[1].replace("%", "\\%").replace("_", "\\_") + "%"

	update(limit_path)
