import sqlalchemy as sa
from ..database import Base

favorites = sa.Table("favorites", Base.metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
    sa.Column("song", sa.Integer, sa.ForeignKey("songs.id"), nullable=False, index=True),
    sa.schema.Index("uniq_favorite", "user_id", "song", unique=True)
)
