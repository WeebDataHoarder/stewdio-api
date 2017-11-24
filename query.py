#!/usr/bin/env python3

import sys
import psycopg2
from psycopg2.extras import DictCursor
from parse import parse


BASE_QUERY = '''
SELECT
    songs.id AS id,
    songs.hash AS hash,
    songs.title AS title,
    artists.name AS artist,
    albums.name AS album,
    songs.location AS path,
    songs.length AS duration,
    array_remove(array_agg(DISTINCT tags.name), NULL) AS tags,
    array_remove(array_agg(DISTINCT users.nick), NULL) AS favored_by
FROM songs
JOIN artists ON songs.artist = artists.id
JOIN albums ON songs.album = albums.id
LEFT JOIN favorites ON songs.id = favorites.song
LEFT JOIN users ON favorites.account = users.id
LEFT JOIN taggings ON songs.id = taggings.song
LEFT JOIN tags ON taggings.tag = tags.id
GROUP BY songs.id, songs.title, artists.name, albums.name
HAVING {where}
'''

conn = psycopg2.connect(dbname='music')
c = conn.cursor(cursor_factory=DictCursor)


q = """
(artist:mizuki OR artist:水樹) AND NOT fav:minus AND album:'supernal liberty'
"""
if len(sys.argv) > 1:
    q = ' '.join(sys.argv[1:])
print("original query from user input:")
print(q)

where = parse(q).build()
q = BASE_QUERY.format(where=where)
print("generated SQL query:")
print(c.mogrify(q).decode())
c.execute(q)

for row in map(dict, c):
    print(row)
