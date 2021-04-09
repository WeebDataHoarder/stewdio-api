import sqlalchemy as sa
import sqlalchemy_utils as sau

from ..database import Base
from enum import Enum

class SongStatus(Enum):
    broken = "broken"
    missing_data = "missing_data"
    active = "active"
    removed = "removed"
    unlisted = "unlisted"

class Song(Base):
    __tablename__ = "songs"
    id = sa.Column(sa.Integer, primary_key=True)
    title = sa.Column(sa.Text)
    path = sa.Column(sa.Text, nullable=False)
    duration = sa.Column(sa.Integer)
    hash = sa.Column(sa.Text, unique=True)
    audio_hash = sa.Column(sa.Text)
    added = sa.Column(sa.DateTime, server_default=sa.func.now())

    status = sa.Column(
            sau.ChoiceType(SongStatus, impl=sa.String()),
            nullable=False)

    artist_id = sa.Column(sa.Integer,
            sa.ForeignKey("artists.id"),
            name="artist")
    artist = sa.orm.relationship("Artist",
            back_populates="songs")

    album_id = sa.Column(sa.Integer,
            sa.ForeignKey("albums.id"),
            name="album")
    album = sa.orm.relationship("Album",
            back_populates="songs")

    favored_by = sa.orm.relationship("User",
            secondary="favorites",
            collection_class=set,
            back_populates="favorites")

    tags = sa.orm.relationship("Tag",
            secondary="taggings",
            collection_class=set,
            back_populates="songs")

    favorite_count = sa.Column(sa.Integer,
            default=0,
            server_default=sa.text('0'),
            nullable=False,
            index=True)
    tag_count = sa.Column(sa.Integer,
            default=0,
            server_default=sa.text('0'),
            nullable=False,
            index=True)
    play_count = sa.Column(sa.Integer,
            default=0,
            server_default=sa.text('0'),
            nullable=False,
            index=True)
    score = sa.Column(sa.Integer,
            default=0,
            server_default=sa.text('0'),
            nullable=False,
            index=True)

    cover_id = sa.Column(sa.BIGINT,
            sa.ForeignKey("covers.id"),
            name="cover")
    cover = sa.orm.relationship("Cover",
            back_populates="songs")

    mb_metadata = sa.Column(sa.JSON().with_variant(sa.dialects.postgresql.JSONB(none_as_null=True), 'postgresql'))
    song_metadata = sa.Column(sa.JSON().with_variant(sa.dialects.postgresql.JSONB(none_as_null=True), 'postgresql'))
    lyrics = sa.Column(sa.JSON().with_variant(sa.dialects.postgresql.JSONB(none_as_null=True), 'postgresql'))

    def json(self):
        return dict(
            **{attr: getattr(self, attr)
               for attr in ('id', 'title', 'path', 'duration', 'hash', 'play_count', 'audio_hash', 'song_metadata')},
            album=self.album.name if self.album else None,
            artist=self.artist.name if self.artist else None,
            cover=self.cover_id,
            status=self.status.value,
            favored_by=[u.name for u in self.favored_by],
            tags=[t.name for t in self.tags],
            lyrics=(list(dict(self.lyrics).keys()) if self.lyrics else []),
        )

    def __str__(self):
        return f"{self.title} by {self.artist} from {self.album}"
