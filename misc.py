import config

import json
import flask
from functools import wraps
import psycopg2.extras


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
			json.dumps(ret),
			status=status,
			headers={
				"Content-Type": "application/json",
			}
		)
	return wrapper

def song_hash2id(*keyword_names):
	def decorator(fn):
		@wraps(fn)
		def wrapper(*args, **kwargs):
			if "cur" not in kwargs:
				raise RuntimeError("DB connection injection is required")
			cur = kwargs["cur"]
			for keyword_name in keyword_names:
				if keyword_name in kwargs:
					arg = kwargs[keyword_name]
					int(arg, 16)  # sanity check
					arg += "%"
					cur.execute("SELECT id FROM songs WHERE hash ILIKE %s", (arg,))
					kwargs[keyword_name] = cur.fetchone()[0]
			return fn(*args, **kwargs)
		return wrapper
	return decorator
