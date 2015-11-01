import config

import os
from whoosh import fields
from whoosh.filedb.filestore import FileStorage


class StewdioSchema(fields.SchemaClass):
	id = fields.ID(stored=True, unique=True)
	hash = fields.ID(stored=True, unique=True)
	path = fields.TEXT(stored=True)
	title = fields.NGRAM(stored=True, phrase=True)
	artist = fields.NGRAM(stored=True, phrase=True)
	album = fields.NGRAM(stored=True, phrase=True)
	duration = fields.NUMERIC(stored=True)
	status = fields.KEYWORD(stored=True)
	tags = fields.KEYWORD(commas=True)

storage = FileStorage(str(config.index_dir))

if not storage.index_exists():
	os.makedirs(str(config.index_dir))
	ix = storage.create_index(StewdioSchema)
else:
	ix = storage.open_index()
