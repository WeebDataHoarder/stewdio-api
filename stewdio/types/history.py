import sqlalchemy as sa

from ..database import Base

class History(Base):
    __tablename__ = "history"
    id = sa.Column(sa.BIGINT, primary_key=True)
    play_time = sa.Column(sa.TIMESTAMP(timezone=True), nullable=False)
    data = sa.Column(sa.JSON(), nullable=False)
