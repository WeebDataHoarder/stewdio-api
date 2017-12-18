from contextlib import contextmanager
from typing import Set

from geventwebsocket import WebSocketError
from geventwebsocket.websocket import WebSocket

clients: Set[WebSocket] = set()


# @contextmanager
def register_client(ws: WebSocket):
	clients.add(ws)
	try:
		# yield
		while ws.receive():
			pass
	finally:
		clients.remove(ws)


def publish(msg):
	for ws in clients:
		try:
			ws.send(msg)
		except WebSocketError:
			pass
