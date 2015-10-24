import os

import config

from whoosh import fields
from whoosh.filedb.filestore import FileStorage


class StewdioSchema(fields.SchemaClass):
	id = fields.ID(stored=True, unique=True)
	hash = fields.ID(stored=True, unique=True)
	path = fields.ID(stored=True, unique=True)
	title = fields.TEXT(stored=True)
	artist = fields.TEXT(stored=True)
	album = fields.TEXT(stored=True)
	duration = fields.NUMERIC(stored=True)
	status = fields.KEYWORD(stored=True)

storage = FileStorage(str(config.index_dir))

if not storage.index_exists():
	os.makedirs(str(config.index_dir))
	ix = storage.create_index(StewdioSchema)
else:
	ix = storage.open_index()
