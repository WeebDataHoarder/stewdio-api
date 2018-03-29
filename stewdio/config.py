import configparser
import logging
import re
from psycopg2.pool import ThreadedConnectionPool

from .database import Database

config = configparser.ConfigParser()
config.read(['/etc/stewdio/api.conf', 'stewdio-api.conf'])

fmt = logging.Formatter("[%(asctime)s] %(levelname)s: %(filename)s:%(funcName)s(%(lineno)s): %(message)s")
logger = logging.getLogger("stewdio")
logger.setLevel(logging.DEBUG)

# stderr logging
sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)
sh.setFormatter(fmt)
logger.addHandler(sh)

kawa_api = config['kawa']['url']
if not kawa_api.endswith('/'):
    kawa_api += '/'

cfg_pg: configparser.SectionProxy = config['postgres']
postgres = ThreadedConnectionPool(
    minconn=int(cfg_pg['minconn']),
    maxconn=int(cfg_pg['maxconn']),
    database=cfg_pg['database'],
    user=cfg_pg['user'],
    password=cfg_pg['password'],
    host=cfg_pg['host'],
    port=int(cfg_pg['port']),
)

db = Database(f"postgresql://{cfg_pg['user']}:{cfg_pg['password']}@{cfg_pg['host']}:{cfg_pg['port']}/{cfg_pg['database']}")

cfg_search: configparser.SectionProxy = config['search']
off_vocal_regex = cfg_search.get('off-vocal-regex')
if off_vocal_regex:
    re.compile(off_vocal_regex)  # verify

cfg_storage_status: configparser.SectionProxy = config['storage-status']
storage_status = dict(cfg_storage_status)


cfg_acoustid: configparser.SectionProxy = config['acoustid']
acoustid_api_key = cfg_acoustid.get('api-key')
