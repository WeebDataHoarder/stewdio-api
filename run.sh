#!/bin/bash

cd "$(dirname "$0")"

source venv3/bin/activate
export LANGUAGE=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
export LC_TYPE=en_US.UTF-8
exec gunicorn -b 127.0.0.1:8011 --threads 2 --timeout 600 --worker-class flask_sockets.worker stewdio.app:app
