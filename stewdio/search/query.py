#!/usr/bin/env python3
from .ast import Qualified, String
from .parse import parse
from psycopg2.sql import SQL, Literal

BASE_QUERY = SQL('''
SELECT
    songs.id AS id,
    songs.hash AS hash,
    songs.title AS title,
    (SELECT artists.name FROM artists WHERE songs.artist = artists.id LIMIT 1) AS artist,
    (SELECT albums.name FROM albums WHERE songs.album = albums.id LIMIT 1) AS album,    
    songs.path AS path,
    songs.duration AS duration,
    songs.status AS status,
    songs.cover AS cover,
    ARRAY(SELECT jsonb_object_keys(songs.lyrics)) AS lyrics,
    songs.favorite_count AS favorite_count,
    songs.play_count AS play_count,
    songs.audio_hash AS audio_hash,
    songs.song_metadata AS song_metadata,
    ARRAY(SELECT tags.name FROM tags JOIN taggings ON (taggings.tag = tags.id) WHERE taggings.song = songs.id) AS tags,
    ARRAY(SELECT users.name FROM users JOIN favorites ON (favorites.user_id = users.id) WHERE favorites.song = songs.id) AS favored_by
FROM songs
{where}
''')


def search(cursor, context, query, limit=None, order_by=' ORDER BY album ASC, path ASC '):
    where = SQL("WHERE songs.status = 'active' AND ") + parse(query).build(context)
    q = BASE_QUERY.format(where=where)
    q += SQL(order_by)
    if limit:
        q += SQL(' LIMIT ') + Literal(limit)
    cursor.execute(q)
    return [dict(r) for r in cursor]


def search_favorites(cursor, user, order_by=' ORDER BY album ASC, path ASC '):
    q = BASE_QUERY.format(where=SQL(' WHERE ') + Qualified('fav', String(user)).build(None))
    q += SQL(order_by)
    cursor.execute(q, (user,))
    return [dict(r) for r in cursor]


def get_random(cursor, query, off_vocal_regex=None):
    if query == '':
        where = SQL("WHERE songs.status = 'active'")
    else:
        where = SQL("WHERE songs.status = 'active' AND ") + parse(query).build(None)

    if off_vocal_regex:
        where += SQL(' AND title !~* ') + Literal(off_vocal_regex)
    q = BASE_QUERY.format(where=where)
    q += SQL(' ORDER BY random()')
    q += SQL(' LIMIT 1')
    cursor.execute(q)
    return dict(cursor.fetchone())


if __name__ == '__main__':
    import sys
    import psycopg2
    from psycopg2.extras import DictCursor
    conn = psycopg2.connect(dbname='music')
    cursor = conn.cursor(cursor_factory=DictCursor)

    q = """
    (artist:mizuki OR artist:水樹) AND NOT fav:minus AND album:'supernal liberty' AND duration>10
    """
    if len(sys.argv) > 1:
        q = ' '.join(sys.argv[1:])
    print("original query from user input:")
    print(q)

    where = parse(q).build(None)
    q = BASE_QUERY.format(where=SQL(''))
    q += SQL(' WHERE ') + where
    print("generated SQL condition:")
    print(where)
    print("generated SQL query:")
    print(cursor.mogrify(q).decode())
    cursor.execute(q)

    for row in map(dict, cursor):
        print(row)
