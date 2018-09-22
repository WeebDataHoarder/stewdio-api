import sqlalchemy as sa

from stewdio.database import Base

taggings = sa.Table("taggings", Base.metadata,
    sa.Column("song", sa.Integer, sa.ForeignKey("songs.id"), nullable=False, index=True, primary_key=True),
    sa.Column("tag", sa.Integer, sa.ForeignKey("tags.id"), nullable=False, index=True, primary_key=True)
)
