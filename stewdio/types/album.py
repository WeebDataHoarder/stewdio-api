import sqlalchemy as sa
from ..database import Base

class Album(Base):
    __tablename__ = "albums"
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.Text, nullable=False)
    songs = sa.orm.relationship("Song",
            collection_class=set,
            back_populates="album")

    def __str__(self):
        return str(self.name)
