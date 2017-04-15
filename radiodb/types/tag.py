import sqlalchemy as sa
from radiodb.database import Base

taggings = Table("taggings", Base.metadata,
    Column("song", Integer, ForeignKey("songs.id")),
    Column("tag", Integer, ForeignKey("tags.id"))
)

class Tag(Base):
    __tablename__ = "tags"
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.Text, nullable=False, unique=True)
    songs = sa.orm.relationship("Song",
            secondary=taggings,
            backref="tags")
