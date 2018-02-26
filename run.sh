#!/bin/bash

cd "$(dirname "$0")"

source venv3/bin/activate

exec gunicorn -b 127.0.0.1:8011 --timeout 600 --worker-class flask_sockets.worker stewdio.app:app
