import sqlalchemy as sa
from ..database import Base

class Artist(Base):
    __tablename__ = "artists"
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.Text, nullable=False)
    songs = sa.orm.relationship("Song",
            collection_class=set,
            back_populates="artist")
