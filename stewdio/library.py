import hashlib
import logging
import os
from functools import partial
from operator import attrgetter
from pathlib import Path
from typing import NamedTuple

import acoustid
from acoustid import WebServiceError
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


def augment_with_musicbrainz_metadata(song):
	meta = 'recordings releases'
	try:
		data = acoustid.match(config.acoustid_api_key, song.path, meta=meta, parse=False)
		if data.get('status') != 'ok':
			raise WebServiceError("status not ok")
		if not isinstance(data.get('results'), list):
			raise WebServiceError("invalid results")
		song.mb_metadata = data['results']
		L.debug(f"Augmented {song} with MusicBrainz metadata")
	except WebServiceError as e:
		L.exception("Failed to fetch MusicBrainz metadata")


def update(session, scan_dir):
	songs = []
	scan_dir = Path(scan_dir)
	L.info(f"Scanning directory {scan_dir} for new files")
	for root, dirs, files in os.walk(scan_dir):
		root = Path(root)
		for path in sorted(files):
			path = root / path
			path = path.absolute()
			if path.suffix not in ('.flac', '.mp3', '.aac', '.opus', '.ogg'):
				continue
			L.debug(f"Found path {path}")
			hash = compute_hash(path)
			song = session.query(Song).filter_by(hash=hash).one_or_none()
			if song:
				if not song.mb_metadata:
					augment_with_musicbrainz_metadata(song)
				L.info(f"Song {song} (path: {song.path}) already exists in database (new path: {path}), skipping")
				continue
			if session.query(Song).filter_by(path=str(path)).exists():
				raise RuntimeError(f"File {path} found in database but hash mismatches, aborting")
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
			augment_with_musicbrainz_metadata(song)
			session.add(song)
			session.flush()
			L.info(f"Added song {song}")
			songs.append(song)
	return songs


if __name__ == '__main__':
	import argparse
	p = argparse.ArgumentParser()
	sp = p.add_subparsers(dest='command')
	addp = sp.add_parser('add')
	addp.add_argument('dirs', nargs='+', type=Path)
	replacep = sp.add_parser('replace')
	replacep.add_argument('old', type=Path)
	replacep.add_argument('new', type=Path)
	args = p.parse_args()
	session = config.db.create_session()
	if not args.command:
		p.error("No command specified")
	elif args.command == 'add':
		for path in args.dirs:
			update(session, path)
			session.commit()
	elif args.command == 'replace':
		old = (session.query(Song)
			.filter(Song.path.startswith(str(args.old))).all())
		new = (session.query(Song)
			.filter_by(status=SongStatus.active)
			.filter(Song.path.startswith(str(args.new))).all())
		old.sort(key=attrgetter('path'))
		new.sort(key=attrgetter('path'))
		for old_song, new_song in zip(old, new):
			print("old:", old_song.path)
			print("new:", new_song.path)
			new_song.favored_by.update(old_song.favored_by)
			old_song.favored_by.clear()
			old_song.status = SongStatus.removed
			print("---")
		if len(old) != len(new):
			p.exit(status=-1, message="Different number of files, cannot replace")
		if input("Replace songs? (y/n) ") != 'y':
			p.exit()
		session.commit()
