import hashlib
import logging
import os
# import chardet
import re
import audioread
import zlib
from ftfy import fix_text
from functools import partial
from operator import attrgetter
from pathlib import Path
from typing import NamedTuple

from PIL import Image
from io import BytesIO

import acoustid
from acoustid import WebServiceError
from tinytag import TinyTag, TinyTagException
import magic
import warnings

from stewdio.types.song import SongStatus
from . import config
from .types import Artist, Album, Song, Cover

L = logging.getLogger("stewdio.library")


class Metadata(NamedTuple):
    artist: str
    album: str
    title: str
    duration: int


def compute_audio_hash(file):
    a = audioread.audio_open(file)
    h = hashlib.md5()
    crc = 0
    for buf in a:
        h.update(buf)
        crc = zlib.crc32(buf, crc) & 0xffffffff
    return h.hexdigest(), '{:08x}'.format(crc)


def compute_hash(file):
    h = hashlib.md5()
    with file.open('rb') as f:
        for chunk in iter(partial(f.read, 2 ** 14), b''):
            h.update(chunk)
    return h.hexdigest()


def compute_hash_string(str):
    return hashlib.md5(str).hexdigest()


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


def tryFixText(str):
    try:
        try:
            return fix_text(str, fix_entities=False, remove_terminal_escapes=True, fix_encoding=True,
                                 fix_latin_ligatures=True, fix_character_width=False, uncurl_quotes=False,
                                 fix_line_breaks=True, fix_surrogates=True, remove_control_chars=True, remove_bom=True,
                                 normalization='NFC', max_decode_length=1000000).replace('\x00', '')
        except Exception as e:
            return str.replace('\x00', '')
    except Exception as e:
        return ''


def update(session, scan_dir, force=False):
    songs = []
    scan_dir = Path(scan_dir)
    L.info(f"Scanning directory {scan_dir} for new files")
    warnings.simplefilter('error', Image.DecompressionBombWarning)
    for root, dirs, files in os.walk(scan_dir):
        root = Path(root)
        for path in sorted(files):
            try:
                path = root / path
                path = path.absolute()
                if path.suffix.lower() not in (
                        '.flac', '.mp3', '.m4a', '.aac', '.opus', '.ogg', '.tta', '.wav', '.alac', '.caf' '.aiff',
                        '.aif'):
                    continue
                L.debug(f"Found path {path}")
                existingSong = session.query(Song).filter_by(path=str(path)).one_or_none()
                if not force and existingSong:
                    L.info(f"Song {existingSong} (path: {existingSong.path}) already exists in database, skipping")
                    continue
                hash = compute_hash(path)
                existingSong = session.query(Song).filter_by(hash=hash).one_or_none()
                if existingSong and not force:
                    if not existingSong.mb_metadata:
                        augment_with_musicbrainz_metadata(existingSong)
                    L.info(
                        f"Song {existingSong} (path: {existingSong.path}, hash: {existingSong.hash}) already exists in database (new path: {path}), skipping")
                    continue
                metadata = TinyTag.get(str(path), tags=True, duration=True, image=True)
                if existingSong and existingSong.song_metadata:
                    song_metadata = existingSong.song_metadata
                else:
                    song_metadata = {}

                if not metadata.artist:
                    metadata.artist = metadata.albumartist

                # Undo the mess TinyTag causes when unknown encoding happens
                artistStr = tryFixText(metadata.artist)
                albumStr = tryFixText(metadata.album)
                titleStr = tryFixText(metadata.title)

                artist = session.query(Artist).filter_by(name=artistStr).one_or_none()
                if not artist and metadata.artist:
                    artist = Artist(name=artistStr)
                    L.debug(f"Creating artist {artist}")
                album = session.query(Album).filter_by(name=albumStr).one_or_none()
                if not album and metadata.album:
                    album = Album(name=albumStr)
                    L.debug(f"Creating album {album}")

                if existingSong:
                    existingSong.title = titleStr
                    existingSong.path = str(path)
                    existingSong.duration = int(metadata.duration)
                    existingSong.hash = hash
                    existingSong.artist = artist
                    existingSong.album = album
                    if not existingSong.audio_hash:
                        try:
                            audio_hash, crc32 = compute_audio_hash(path)
                            existingSong.audio_hash = audio_hash
                            song_metadata['audio_crc'] = crc32
                        except Exception as e:
                            L.info(f"Failed to hash audio data {path}: {e}")
                    existingSong.song_metadata = song_metadata
                    song = existingSong
                else:
                    audio_hash = None
                    crc32 = None
                    try:
                        audio_hash, crc32 = compute_audio_hash(path)
                        song_metadata['audio_crc'] = crc32
                    except Exception as e:
                        L.info(f"Failed to hash audio data {path}: {e}")
                    song = Song(
                        title=titleStr,
                        path=str(path),
                        duration=int(metadata.duration),
                        hash=hash,
                        status=SongStatus.active,
                        artist=artist,
                        album=album,
                        audio_hash=audio_hash,
                        song_metadata=song_metadata
                    )

                if not song.mb_metadata:
                    augment_with_musicbrainz_metadata(song)

                cover = None
                image_type = None
                image_data = metadata.get_image()
                if image_data:
                    image_type = "embedded"

                if not image_type:
                    for filename in os.listdir(os.path.dirname(path)):
                        fullPath = os.path.join(os.path.dirname(path), filename)
                        if re.search(r'^(cover|folder|front|front[_\- ]cover|cd|disc)[ _0-9]*\.(jpe?g|png)$', filename,
                                     re.IGNORECASE) and os.path.isfile(fullPath):
                            try:
                                image_data = open(fullPath, 'rb').read()
                                image_type = "file"
                                break
                            except Exception as e:
                                L.info(f"Failed to open cover file {fullPath}: {e}")

                # if not image_type and song.mb_metadata:
                # TODO: fetch covers from MusicBrainz

                if image_type and image_data:
                    L.info(f"Found {image_type} type image!")

                    image_hash = compute_hash_string(image_data)
                    cover = session.query(Cover).filter_by(hash=image_hash).one_or_none()
                    if not cover:
                        L.info(f"Creating new cover")
                        try:
                            image_mime = magic.from_buffer(image_data, mime=True)
                            L.info(f"Cover mime type: {image_mime}")
                        except Exception as e:
                            L.info(f"Could not guess mime type: {e}")
                            image_mime = "image/jpeg"

                        try:
                            im = Image.open(BytesIO(image_data))
                            thumb_small = im.copy()
                            thumb_small.thumbnail((55, 55), Image.LANCZOS)
                            small = BytesIO()
                            thumb_small.save(small, format='JPEG', quality=80, optimize=True, progressive=True)
                            thumb_large = im.copy()
                            thumb_large.thumbnail((800, 800), Image.LANCZOS)
                            large = BytesIO()
                            thumb_large.save(large, format='JPEG', quality=95, optimize=True, progressive=True)
                            cover = Cover(hash=image_hash, type=image_type, mime=image_mime, data=image_data,
                                          thumb_small=small.getvalue(), thumb_large=large.getvalue())
                        except Exception as e:
                            L.info(f"Failed to create thumbnails: {e}")
                            cover = Cover(hash=image_hash, type=image_type, mime=image_mime, data=image_data)

                        song.cover = cover
                    else:
                        L.info(f"Found existing cover")
                        song.cover = cover

                if existingSong:
                    existingSong = song
                    session.flush()
                    L.info(f"Updated song {existingSong}")
                    songs.append(existingSong)
                else:
                    session.add(song)
                    session.flush()
                    L.info(f"Added song {song}")
                    songs.append(song)

            except Exception as e:
                L.exception(f"Error adding track")
    return songs


if __name__ == '__main__':
    import argparse

    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest='command')
    addp = sp.add_parser('add')
    addp.add_argument('dirs', nargs='+', type=Path)
    addfp = sp.add_parser('addforce')
    addfp.add_argument('dirs', nargs='+', type=Path)
    replacep = sp.add_parser('replace')
    replacep.add_argument('old', type=Path)
    replacep.add_argument('new', type=Path)
    movep = sp.add_parser('move',
                          help="Move files from one directory to another " +
                               "(in the database only, not in the file system) " +
                               "and set status to active")
    movep.add_argument('old', type=Path)
    movep.add_argument('new', type=Path)
    args = p.parse_args()
    session = config.db.create_session()
    if not args.command:
        p.error("No command specified")
    elif args.command == 'add':
        for path in args.dirs:
            update(session, path, False)
            session.commit()
    elif args.command == 'addforce':
        for path in args.dirs:
            update(session, path, True)
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
            new_song.tags.update(old_song.tags)
            old_song.favored_by.clear()
            old_song.status = SongStatus.removed
            print("---")
        if len(old) != len(new):
            p.exit(status=-1, message="Different number of files, cannot replace")
        if input("Replace songs? (y/n) ") != 'y':
            p.exit()
        session.commit()
    elif args.command == 'move':
        old = (session.query(Song)
               .filter(Song.path.startswith(str(args.old))).all())
        for song in old:
            new_path = args.new / Path(song.path).relative_to(args.old)
            print("old (", song.status, "):", song.path)
            print("new:", new_path)
            song.path = str(new_path)
            song.status = SongStatus.active
            print("---")
        if input("Move songs? (y/n) ") != 'y':
            p.exit()
        session.commit()
