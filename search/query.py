#!/usr/bin/env python3

from .parse import parse


BASE_QUERY = '''
SELECT
    songs.id AS id,
    songs.hash AS hash,
    songs.title AS title,
    artists.name AS artist,
    albums.name AS album,
    songs.location AS path,
    songs.length AS duration,
    songs.status AS status,
    array_remove(array_agg(DISTINCT tags.name), NULL) AS tags,
    array_remove(array_agg(DISTINCT users.nick), NULL) AS favored_by
FROM songs
JOIN artists ON songs.artist = artists.id
JOIN albums ON songs.album = albums.id
LEFT JOIN favorites ON songs.id = favorites.song
LEFT JOIN users ON favorites.account = users.id
LEFT JOIN taggings ON songs.id = taggings.song
LEFT JOIN tags ON taggings.tag = tags.id
{where}
GROUP BY
    songs.id,
    songs.hash,
    songs.title,
    artists.name,
    albums.name,
    songs.location,
    songs.length,
    songs.status
'''


def search(cursor, query, limit=None):
    where = "WHERE songs.status = 'active'"
    having = parse(query).build()
    q = BASE_QUERY.format(where=where)
    q += f' HAVING {having}'
    if limit:
        q += f' LIMIT {limit}'
    cursor.execute(q)
    return [dict(r) for r in cursor]


def search_by_hash(cursor, hash):
    q = BASE_QUERY.format(where='')
    q += " HAVING songs.hash ILIKE %s || '%%'"
    cursor.execute(q, (hash,))
    if cursor.rowcount > 1:
        raise ValueError(f"Expected one result, got {cursor.rowcount}")
    elif cursor.rowcount == 0:
        return None
    return dict(cursor.fetchone())

def search_favorites(cursor, user):
    q = BASE_QUERY.format(where='')
    q += " HAVING ARRAY[%s] <@ array_agg(users.nick)"
    cursor.execute(q, (user,))
    return [dict(r) for r in cursor]

def get_random(cursor):
    where = "WHERE songs.status = 'active'"
    q = BASE_QUERY.format(where=where)
    q += ' ORDER BY random()'
    q += ' LIMIT 1'
    cursor.execute(q)
    return dict(cursor.fetchone())


if __name__ == '__main__':
    import sys
    import psycopg2
    from psycopg2.extras import DictCursor
    conn = psycopg2.connect(dbname='music')
    cursor = conn.cursor(cursor_factory=DictCursor)

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
    print(cursor.mogrify(q).decode())
    cursor.execute(q)

    for row in map(dict, cursor):
        print(row)
