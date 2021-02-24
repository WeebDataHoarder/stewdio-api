from contextlib import contextmanager

from . import config

import json
import flask
from functools import wraps
import psycopg2.extras
import psycopg2.extensions

psycopg2.extensions.register_adapter(dict, psycopg2.extras.Json)


def with_pg_cursor(fn):
    """
	Injects an argument `cur` containing a postgres cursor into the function arguments. Autocommits.
	"""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "cur" in kwargs:
            # pg cursor is given by the caller already, which also takes care of committing
            return fn(*args, **kwargs)
        conn = config.postgres.getconn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        kwargs["cur"] = cur
        try:
            ret = fn(*args, **kwargs)
            conn.commit()
            return ret
        except:
            conn.rollback()
            raise
        finally:
            config.postgres.putconn(conn)

    return wrapper


def json_api(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        ret = fn(*args, **kwargs)
        status = None
        if isinstance(ret, flask.Response):
            return ret
        if isinstance(ret, tuple):
            status = ret[1]
            ret = ret[0]
        return flask.Response(
            json.dumps(ret, ensure_ascii=False, separators=(',', ':')),
            status=status,
            headers={
                "Content-Type": "application/json; charset=utf-8",
            }
        )

    return wrapper


def with_db_session(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "session" in kwargs:
            raise RuntimeError("A session argument already exists!")
        with db_session() as s:
            kwargs["session"] = s
            return fn(*args, **kwargs)

    return wrapper


@contextmanager
def db_session():
    session = config.db.create_session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
