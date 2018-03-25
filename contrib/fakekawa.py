#!/usr/bin/env python3
"""
Tool to simulate kawa. Prevents stewdio-api from throwing errors when developing.
"""

import flask
import json

app = flask.Flask(__name__)

@app.route('/listeners')
def listeners():
    return json.dumps(
[
  {
    "mount": "stream256.opus",
    "path": "/stream256.opus?user=ac",
    "headers": [
      {
        "name": "Host",
        "value": "radio.stew.moe"
      },
      {
        "name": "Connection",
        "value": "close"
      },
      {
        "name": "User-Agent",
        "value": "mpv 0.27.0"
      },
      {
        "name": "Accept",
        "value": "*/*"
      },
      {
        "name": "Range",
        "value": "bytes=0-"
      },
      {
        "name": "Icy-MetaData",
        "value": "1"
      }
    ]
  },
  {
    "mount": "stream192.mp3",
    "path": "/stream192.mp3?user=Luminarys",
    "headers": [
      {
        "name": "Host",
        "value": "radio.stew.moe"
      },
      {
        "name": "Connection",
        "value": "close"
      },
      {
        "name": "User-Agent",
        "value": "mpv 0.18.0"
      },
      {
        "name": "Accept",
        "value": "*/*"
      },
      {
        "name": "Range",
        "value": "bytes=0-"
      },
      {
        "name": "Icy-MetaData",
        "value": "1"
      }
    ]
  },
  {
    "mount": "stream256.opus",
    "path": "/stream256.opus?user=minus2",
    "headers": [
      {
        "name": "Host",
        "value": "radio.stew.moe"
      },
      {
        "name": "Connection",
        "value": "close"
      },
      {
        "name": "User-Agent",
        "value": "Music Player Daemon 0.20.13"
      },
      {
        "name": "Accept",
        "value": "*/*"
      },
      {
        "name": "Icy-Metadata",
        "value": "1"
      }
    ]
  }
])

@app.route('/queue')
def queue():
    return json.dumps(
[
  {
    "album": "test",
    "artist": "test",
    "duration": 60,
    "favored_by": [
      "minus"
    ],
    "hash": "00000000000000000000000000000000",
    "id": 123,
    "path": "/tmp/test.flac",
    "status": "active",
    "tags": ["test"],
    "title": "test"
  }
])


@app.route('/<path:path>', methods=['GET', 'POST', 'DELETE', 'PUT'])
def asdf(path):
    return ""

if __name__ == "__main__":
    app.run(port=4040)
