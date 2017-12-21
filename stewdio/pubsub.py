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


def _make_publisher(type: str):
	def publisher(self, msg: Any):
		self.publish(dict(type=type, data=msg))
	publisher.__name__ = type
	return publisher

class EventPublisher(Publisher):
	playing = _make_publisher('playing')
	listeners = _make_publisher('listeners')
	favorite = _make_publisher('favorite')
	queue = _make_publisher('queue')


playing = Publisher()
events = EventPublisher()
