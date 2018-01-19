import sqlalchemy as sa

from ..database import Base

class User(Base):
    __tablename__ = "users"
    id = sa.Column(sa.Integer, primary_key=True)
    nick = sa.Column(sa.Text, nullable=False)

    favorites = sa.orm.relationship("Song",
            secondary="favorites",
            collection_class=set,
            back_populates="favored_by")

    __table_args__ = (sa.schema.Index("uniq_nick", "nick", unique=True),)
