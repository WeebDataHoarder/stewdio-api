#!/usr/bin/env python3

import stewdio
from stewdio.types import *
import os
from tqdm import tqdm

session = stewdio.config.db.create_session()

q = session.query(Song).filter_by(status="active")
for s in tqdm(q, total=q.count()):
    if not os.path.exists(s.location):
        tqdm.write(s.location)
