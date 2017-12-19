from typing import Set

import gevent
from geventwebsocket import WebSocketError
from geventwebsocket.websocket import WebSocket

clients: Set[WebSocket] = set()


def pinger(ws: WebSocket):
	try:
		while True:
			gevent.sleep(10)
			ws.send_frame(b'', WebSocket.OPCODE_PING)
	except WebSocketError:
		pass


def register_client(ws: WebSocket):
	gevent.spawn(pinger, ws)
	clients.add(ws)
	try:
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
