#!/bin/bash

cd "$(dirname "$0")"

source venv3/bin/activate

exec uwsgi -s /tmp/uwsgi-stewdio-web-api.sock --chmod-socket=666 --module app --callable app