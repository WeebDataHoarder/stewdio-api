import config

import json
import flask
from functools import wraps


def with_pg_cursor(*cur_args, **cur_kwargs):
	"""
	Injects an argument `cur` containing a postgres cursor into the function arguments. Autocommits.
	"""
	def decorator(fn):
		@wraps(fn)
		def wrapper(*args, **kwargs):
			if "cur" in kwargs:
				raise TypeError("Function may not have a keyword argument named cur")
			conn = config.postgres.getconn()
			cur = conn.cursor(*cur_args, **cur_kwargs)
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
	return decorator


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
