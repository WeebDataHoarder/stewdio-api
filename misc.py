import json

from database import conn

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
		if isinstance(ret, tuple):
			return tuple([json.dumps(ret[0])] + list(ret[1:]))
		return json.dumps(ret)
	return wrapper
