import sqlalchemy as sa

from ..database import Base

class User(Base):
    __tablename__ = "users"
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.Text, nullable=False)
    password = sa.Column(sa.Text, nullable=True)
    user_metadata = sa.Column(sa.JSON().with_variant(sa.dialects.postgresql.JSONB(none_as_null=True), 'postgresql'), nullable=True)

    favorites = sa.orm.relationship("Song",
            secondary="favorites",
            collection_class=set,
            back_populates="favored_by")

    api_keys = sa.orm.relationship("UserApiKey",
            collection_class=set,
            back_populates="user")

    __table_args__ = (sa.schema.Index("uniq_name", "name", unique=True),)


class UserApiKey(Base):
    __tablename__ = "user_api_keys"
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.Text, nullable=False)
    user_id = sa.Column(sa.Integer,
            sa.ForeignKey("users.id"),
            name="user",
            nullable=False)
    user = sa.orm.relationship("User",
            back_populates="api_keys")
    key = sa.Column(sa.Text, nullable=False, unique=True)

    def json(self, show_key=False):
        ret = dict(id=self.id, name=self.name)
        if show_key:
            ret['key'] = self.key
        return ret
