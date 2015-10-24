#!/usr/bin/env python3
from schema import ix

import sys
from whoosh.qparser import QueryParser
parser = QueryParser("title", ix.schema)
myquery = parser.parse(sys.argv[1])

with ix.searcher() as searcher:
	res = searcher.search(myquery)
	print(len(res))
	for r in res:
		print(r)
