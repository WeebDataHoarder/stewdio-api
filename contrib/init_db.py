#!/usr/bin/env python3

from stewdio.config import db
from stewdio.database import Base
import stewdio.types

db.engine.echo = True
Base.metadata.create_all(bind=db.engine)
