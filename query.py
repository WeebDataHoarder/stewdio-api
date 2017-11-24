#!/usr/bin/env python3

import sys
import psycopg2
from parse import parse

conn = psycopg2.connect(dbname='music')
c = conn.cursor()


q = """
(artist:mizuki OR artist:水樹) AND NOT fav:minus AND album:'supernal liberty'
"""
if len(sys.argv) > 1:
    q = ' '.join(sys.argv[1:])
print("original query from user input:")
print(q)

where = parse(q).build()
q = f'''
SELECT songs.id, songs.hash, songs.title, artists.name, albums.name
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
print("generated SQL query:")
print(c.mogrify(q).decode())
c.execute(q)

for row in c:
    print(row)
