import sqlalchemy as sa
from radiodb.database import Base

taggings = sa.Table("taggings", Base.metadata,
    sa.Column("song", sa.Integer, sa.ForeignKey("songs.id")),
    sa.Column("tag", sa.Integer, sa.ForeignKey("tags.id"))
)

class Tag(Base):
    __tablename__ = "tags"
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.Text, nullable=False, unique=True)
    songs = sa.orm.relationship("Song",
            secondary=taggings,
            backref="tags")
