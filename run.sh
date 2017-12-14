#!/bin/bash

cd "$(dirname "$0")"

source venv3/bin/activate

exec gunicorn -b 127.0.0.1:8011 --worker-class eventlet stewdio:app
