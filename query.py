#!/usr/bin/env python3
from app import search_internal

import sys


res = search_internal(' '.join(sys.argv[1:]))
for r in res:
	print(r)
