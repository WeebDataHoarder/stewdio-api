import sqlalchemy as sa

from ..database import Base


class Tag(Base):
    __tablename__ = "tags"
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.Text, nullable=False, unique=True, index=True)
    songs = sa.orm.relationship("Song",
            secondary="taggings",
            collection_class=set,
            back_populates="tags")
