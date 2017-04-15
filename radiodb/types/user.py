import sqlalchemy as sa
from radiodb.database import Base

class User(Base):
    __tablename__ = "users"
    id = sa.Column(sa.Integer, primary_key=True)
    nick = sa.Column(sa.Text, nullable=False)
