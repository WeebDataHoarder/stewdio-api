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

    def json(self):
        return dict(
            **{attr: getattr(self, attr)
               for attr in ('id', 'title', 'path', 'duration', 'hash')},
            album=self.album.name if self.album else None,
            artist=self.artist.name if self.artist else None,
            status=self.status.value,
            favored_by=[u.nick for u in self.favored_by],
            tags=[t.name for t in self.tags],
        )

    def __str__(self):
        return f"{self.title} by {self.artist} from {self.album}"
