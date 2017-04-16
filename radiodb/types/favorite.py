import sqlalchemy as sa
from radiodb.database import Base

class Favorite(Base):
    __tablename__ = "favorites"
    id = sa.Column(sa.Integer, primary_key=True)

    user_id = sa.Column(sa.Integer,
            sa.ForeignKey("users.id"),
            name="account")
    user = sa.orm.relationship("User", backref=sa.orm.backref("favorites"))

    song_id = sa.Column(sa.Integer,
            sa.ForeignKey("songs.id"),
            name="song")
    song = sa.orm.relationship("Song")

    __table_args__ = (sa.schema.Index("uniq_favorite", "account", "song", unique=True),)
