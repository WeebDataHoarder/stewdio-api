import logging
from datetime import datetime

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker, Session

L = logging.getLogger("stewdio.database")

Base = declarative_base()


class Database:
    def __init__(self, connection_string):
        self.engine = create_engine(connection_string, connect_args={"options": "-c statement_timeout=10000"})

        @event.listens_for(Base, 'before_insert', propagate=True)
        def before_insert(mapper, connection, target):
            if hasattr(target, 'created'):
                target.created = datetime.utcnow()
            if hasattr(target, 'updated'):
                target.updated = datetime.utcnow()

        @event.listens_for(Base, 'before_update', propagate=True)
        def before_update(mapper, connection, target):
            if hasattr(target, 'updated'):
                target.updated = datetime.utcnow()

    def create_session(self) -> Session:
        session = scoped_session(sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine))
        Base.query = session.query_property()

        return session


if __name__ == '__main__':
    from .config import db
    from .types import *

    session = db.create_session()
