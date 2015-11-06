import config

import json
import flask
from functools import wraps


def with_pg_cursor(fn):
	"""
	Injects an argument `cur` containing a postgres cursor into the function arguments. Autocommits.
	"""
	@wraps(fn)
	def wrapper(*args, **kwargs):
		if "cur" in kwargs:
			raise TypeError("Function may not have a keyword argument named cur")
		conn = config.postgres.getconn()
		cur = conn.cursor()
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
			ret = ret[0]
			status = ret[1]
		return flask.Response(
			json.dumps(ret),
			status=status,
			headers={
				"Content-Type": "application/json",
			}
		)
	return wrapper
