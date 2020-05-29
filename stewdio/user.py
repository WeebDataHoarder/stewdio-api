import json
import logging
from functools import wraps
from secrets import token_urlsafe

import flask
from pbkdf2 import crypt

from stewdio.types.user import UserApiKey
from .misc import json_api, with_db_session, db_session
from .types import User

L = logging.getLogger("stewdio.user")

api = flask.Blueprint("user", "user", url_prefix="/api/user")


def requires_auth(fn):
    @wraps(fn)
    def wrapper(*args, session, **kwargs):
        auth = flask.request.authorization
        user = session.query(User).filter_by(name=auth.username).one_or_none() if auth else None
        if not user or crypt(auth.password, user.password) != user.password:
            return flask.Response(
                json.dumps({"error": "authentication required"}),
                status=403
            )
        return fn(*args, user=user, session=session, **kwargs)

    return wrapper


def find_user_by_api_key(session, request):
    key = request.args.get("apikey")
    auth = request.authorization
    if not key and auth:
        key = auth.username if not auth.password else auth.password
    if not key and "authorization" in request.headers:
        key = request.headers["authorization"]
    if not key and "radio-apikey" in request.cookies:
        key = request.cookies["radio-apikey"]
    key = session.query(UserApiKey).filter_by(key=key).one_or_none()
    return key.user if key else None


def check_api_key(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "session" in kwargs:
            key = find_user_by_api_key(kwargs["session"], flask.request)
        else:
            with db_session() as s:
                key = find_user_by_api_key(s, flask.request)
        if not key:
            return flask.Response(
                json.dumps({"error": "authentication required"}),
                status=403
            )
        return fn(*args, **kwargs)

    return wrapper


def requires_api_key(fn):
    @wraps(fn)
    def wrapper(*args, session, **kwargs):
        key = find_user_by_api_key(session, flask.request)
        if not key:
            return flask.Response(
                json.dumps({"error": "authentication required"}),
                status=403
            )
        return fn(*args, user=key, session=session, **kwargs)

    return wrapper


@api.route("/update", methods=["POST"])
@json_api
@with_db_session
@requires_auth
def update(user, session):
    j = flask.request.get_json(force=True)
    user.password = crypt(j['password'])
    return {"status": "password updated"}, 200


@api.route("/apikeys/create", methods=["POST"])
@json_api
@with_db_session
@requires_auth
def create_api_key(user, session):
    j = flask.request.get_json(force=True)
    key = UserApiKey(name=j['name'], key=token_urlsafe(32))
    user.api_keys.add(key)
    session.flush()
    return {"status": "api key created", "key": key.json(show_key=True)}, 201


@api.route("/apikeys")
@json_api
@with_db_session
@requires_auth
def list_api_keys(user, session):
    return [k.json() for k in user.api_keys], 200


@api.route("/info")
@json_api
@with_db_session
@requires_api_key
def list_user_info(user, session):
    return {"user": user.name, "metadata": user.user_metadata}, 200


if __name__ == '__main__':
    import sys
    from . import config

    session = config.db.create_session()
    user = session.query(User).filter_by(name=sys.argv[1]).one()
    password = token_urlsafe(32)
    user.password = crypt(password)
    print(f"Reset password for {user.name} to: {password}")
    session.commit()
