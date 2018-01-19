import sqlalchemy as sa
from ..database import Base

favorites = sa.Table("favorites", Base.metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("account", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
    sa.Column("song", sa.Integer, sa.ForeignKey("songs.id"), nullable=False),
    sa.schema.Index("uniq_favorite", "account", "song", unique=True)
)
