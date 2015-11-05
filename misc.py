from database import conn

import json
import flask
from functools import wraps


def with_cur(fn):
	@wraps(fn)
	def wrapper(*args, **kwargs):
		with conn.cursor() as cur:
			if "cur" in kwargs:
				raise TypeError("Function may not have a keyword argument named cur")
			try:
				kwargs["cur"] = cur
				ret = fn(*args, **kwargs)
				conn.commit()
				return ret
			except:
				conn.rollback()
				raise
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
