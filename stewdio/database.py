from datetime import datetime

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

Base = declarative_base()

class Database:
    def __init__(self, connection_string):
        self.engine = create_engine(connection_string)

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

    def create_session(self) -> scoped_session:
        session = scoped_session(sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine))
        Base.query = session.query_property()

        return session
