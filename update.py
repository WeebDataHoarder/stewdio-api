#!/usr/bin/env python3
import config
from schema import ix
import psycopg2

step_size = 1000

with psycopg2.connect(**config.postgres) as conn:
	with conn.cursor() as cur:
		last_id = cur.execute("SELECT COUNT(*) FROM songs;").fetchone()[0]
		print("Last ID in the database is {}".format(last_id))
		for start in range(0, last_id, step_size):
			end = start + step_size - 1
			print("Inserting/Updating IDs {}-{}…".format(start, end))
			cur.execute("""
				SELECT s.id AS id, s.hash AS hash, s.location AS path,
					s.title AS title, ar.name AS artist, al.name AS album,
					s.length AS duration, s.status AS status
				FROM songs AS s
				LEFT OUTER JOIN artists AS ar ON s.artist = ar.id
				LEFT OUTER JOIN albums AS al ON s.album = al.id
				WHERE s.id BETWEEN %s AND %s;""", (start, end))
			with ix.writer() as writer:
				for row in cur:
					writer.update_document(**row)
