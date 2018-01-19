import sqlalchemy as sa
from radiodb.database import Base

class User(Base):
    __tablename__ = "users"
    id = sa.Column(sa.Integer, primary_key=True)
    nick = sa.Column(sa.Text, nullable=False)

    __table_args__ = (sa.schema.Index("uniq_nick", "nick", unique=True),)
