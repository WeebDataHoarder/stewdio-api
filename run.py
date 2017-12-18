from stewdio.app import app
import os

app.debug = os.environ.get('FLASK_DEBUG', '0') == '1'
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
server = pywsgi.WSGIServer(('', 5000), app, handler_class=WebSocketHandler)
server.serve_forever()
