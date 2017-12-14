from stewdio.app import app, socketio
import os

app.debug = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "on")
socketio.run(app)
