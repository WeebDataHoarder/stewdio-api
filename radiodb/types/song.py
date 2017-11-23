import sqlalchemy as sa
import sqlalchemy_utils as sau
from radiodb.database import Base
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
    location = sa.Column(sa.Text, nullable=False)
    length = sa.Column(sa.Integer)
    hash = sa.Column(sa.Text, unique=True)
    added = sa.Column(sa.DateTime, server_default=sa.func.now())

    status = sa.Column(
            sau.ChoiceType(SongStatus, impl=sa.String()),
            nullable=False)

    artist_id = sa.Column(sa.Integer,
            sa.ForeignKey("artists.id"),
            name="artist")
    artist = sa.orm.relationship("Artist", backref=sa.orm.backref("songs"))

    album_id = sa.Column(sa.Integer,
            sa.ForeignKey("albums.id"),
            name="album")
    album = sa.orm.relationship("Album", backref=sa.orm.backref("albums"))
