import config

import os
from whoosh import fields
from whoosh.filedb.filestore import FileStorage


class StewdioSchema(fields.SchemaClass):
	id = fields.ID(stored=True, unique=True)
	hash = fields.ID(stored=True, unique=True)
	path = fields.TEXT(stored=True)
	title = fields.NGRAM(stored=True, phrase=True, minsize=1)
	artist = fields.NGRAM(stored=True, phrase=True, minsize=1)
	album = fields.NGRAM(stored=True, phrase=True, minsize=1)
	duration = fields.NUMERIC(stored=True)
	status = fields.KEYWORD(stored=True)
	tag = fields.KEYWORD(commas=True)
	fav = fields.KEYWORD(commas=True)

storage = FileStorage(str(config.index_dir))

if not storage.index_exists():
	os.makedirs(str(config.index_dir))
	ix = storage.create_index(StewdioSchema)
else:
	ix = storage.open_index()
