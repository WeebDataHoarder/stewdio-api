import sqlalchemy as sa

from ..database import Base


class Cover(Base):
    __tablename__ = "covers"
    id = sa.Column(sa.BIGINT, primary_key=True)
    hash = sa.Column(sa.Text, unique=True)
    type = sa.Column(sa.Text, nullable=False)
    mime = sa.Column(sa.Text, nullable=False)
    data = sa.Column(sa.LargeBinary, nullable=False)
    thumb_small = sa.Column(sa.LargeBinary, nullable=True)
    thumb_large = sa.Column(sa.LargeBinary, nullable=True)
    songs = sa.orm.relationship("Song",
            collection_class=set,
            back_populates="cover")
