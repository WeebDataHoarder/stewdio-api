import hashlib
import logging
import os
from functools import partial
from pathlib import Path
from typing import NamedTuple

from tinytag import TinyTag

from stewdio.types.song import SongStatus
from . import config
from .types import Artist, Album, Song

L = logging.getLogger("stewdio.library")

class Metadata(NamedTuple):
	artist: str
	album: str
	title: str
	duration: int


def compute_hash(file):
	h = hashlib.md5()
	with file.open('rb') as f:
		for chunk in iter(partial(f.read, 2**14), b''):
			h.update(chunk)
	return h.hexdigest()


def update(session, scan_dir):
	songs = []
	scan_dir = Path(scan_dir)
	L.info(f"Scanning directory {scan_dir} for new files")
	for root, dirs, files in os.walk(scan_dir):
		root = Path(root)
		for file in files:
			path = root / file
			path = path.absolute()
			if path.suffix not in ('.flac', '.mp3', '.aac', '.opus', '.ogg'):
				continue
			L.debug(f"Found path {path}")
			hash = compute_hash(path)
			song = session.query(Song).filter_by(hash=hash).one_or_none()
			if song:
				L.info(f"Song {song} (path: {song.path}) already exists in database (new path: {path}), skipping")
				continue
			metadata = TinyTag.get(str(path))
			if not metadata.artist:
				metadata.artist = metadata.albumartist
			artist = session.query(Artist).filter_by(name=metadata.artist).one_or_none()
			if not artist and metadata.artist:
				artist = Artist(name=metadata.artist)
				L.debug(f"Creating artist {artist}")
			album = session.query(Album).filter_by(name=metadata.album).one_or_none()
			if not album and metadata.album:
				album = Album(name=metadata.album)
				L.debug(f"Creating album {album}")
			song = Song(
				title=metadata.title,
				path=str(path),
				duration=int(metadata.duration),
				hash=hash,
				status=SongStatus.active,
				artist=artist,
				album=album,
			)
			session.add(song)
			session.flush()
			L.info(f"Added song {song}")
			songs.append(song.json())
	return songs


if __name__ == '__main__':
	import sys
	session = config.db.create_session()
	update(session, sys.argv[1])
	session.commit()
