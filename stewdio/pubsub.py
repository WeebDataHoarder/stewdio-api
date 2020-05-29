import json
from typing import Set, Any
import logging

import gevent
from geventwebsocket import WebSocketError
from geventwebsocket.websocket import WebSocket

L = logging.getLogger("stewdio.pubsub")


def pinger(ws: WebSocket):
    try:
        while True:
            gevent.sleep(10)
            ws.send_frame(b'', WebSocket.OPCODE_PING)
    except WebSocketError:
        pass


class Publisher:
    def __init__(self):
        self.clients: Set[WebSocket] = set()

    def register_client(self, ws: WebSocket):
        gevent.spawn(pinger, ws)
        L.info(f"Client {ws} connected")
        self.clients.add(ws)
        try:
            while ws.receive():
                pass
        finally:
            L.info(f"Client {ws} disconnected")
            self.clients.remove(ws)

    def publish(self, msg: Any):
        msg = json.dumps(msg)
        for ws in self.clients:
            try:
                ws.send(msg)
            except WebSocketError:
                pass


def clear_secret_data(msg: Any):
    if "hash" in msg:
        del msg["hash"]
    if "audio_hash" in msg:
        del msg["audio_hash"]
    if "path" in msg:
        del msg["path"]
    if "favored_by" in msg:
        del msg["favored_by"]
    if "tags" in msg:
        del msg["tags"]
    if "source" in msg:
        del msg["source"]
    if "play_count" in msg:
        del msg["play_count"]
    if "status" in msg:
        del msg["status"]
    if "named_listeners" in msg:
        del msg["named_listeners"]
    if "song" in msg:
        msg["song"] = clear_secret_data(msg["song"])
    return msg


def _make_publisher(type: str):
    def publisher(self, msg: Any):
        self.publish(dict(type=type, data=msg))

    publisher.__name__ = type
    return publisher


def _make_basic_publisher(type: str):
    def basic_publisher(self, msg: Any):
        self.publish(dict(type=type, data=clear_secret_data(msg)))

    basic_publisher.__name__ = type
    return basic_publisher


class EventPublisher(Publisher):
    playing = _make_publisher('playing')
    listeners = _make_publisher('listeners')
    favorite = _make_publisher('favorite')
    queue = _make_publisher('queue')


class BasicEventPublisher(Publisher):
    playing = _make_basic_publisher('playing')
    listeners = _make_basic_publisher('listeners')
    queue = _make_basic_publisher('queue')


basic = BasicEventPublisher()
events = EventPublisher()
