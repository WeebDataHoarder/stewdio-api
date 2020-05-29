import logging
import flask

from .misc import json_api, with_db_session
from .user import requires_api_key, check_api_key
from .types import Song, Tag

L = logging.getLogger("stewdio.tagging")

api = flask.Blueprint("tagging", "tagging", url_prefix="/api/tag")


@api.route("/<hash>/add/<tag_name>", methods=["POST"])
@json_api
@with_db_session
@check_api_key
def add(hash, tag_name, session):
    song = session.query(Song).filter(Song.hash.startswith(hash)).one_or_none()
    if not song:
        return {"error": "song does not exist"}, 404
    tag = session.query(Tag).filter_by(name=tag_name).one_or_none()
    if not tag:
        tag = Tag(name=tag_name)
        session.add(tag)

    if tag in song.tags:
        return {"created": False}, 200
    song.tags.add(tag)
    return {"created": True}, 201


@api.route("/<hash>/remove/<tag_name>", methods=["POST"])
@json_api
@with_db_session
@check_api_key
def remove(hash, tag_name, session):
    song = session.query(Song).filter(Song.hash.startswith(hash)).one_or_none()
    if not song:
        return {"error": "song does not exist"}, 404
    tag = session.query(Tag).filter_by(name=tag_name).one_or_none()
    if not tag:
        return {"error": "tag does not exist"}, 404

    if tag not in song.tags:
        return {"removed": False}, 200
    song.tags.remove(tag)
    return {"removed": True}, 201


@api.route("/<hash>")
@json_api
@with_db_session
@check_api_key
def get(hash, session):
    song = session.query(Song).filter(Song.hash.startswith(hash)).one_or_none()
    if not song:
        return {"error": "song does not exist"}, 404
    return {"tags": [t.name for t in song.tags]}, 200
