import configparser
import logging
from psycopg2.pool import ThreadedConnectionPool
from redis import StrictRedis, BlockingConnectionPool

config = configparser.ConfigParser()
config.read(['/etc/stewdio/api.conf', 'stewdio-api.conf'])

kawa_api = config['kawa']['url']
if not kawa_api.endswith('/'):
    kawa_api += '/'

cfg_pg = config['postgres']
postgres = ThreadedConnectionPool(
    minconn=int(cfg_pg['minconn']),
    maxconn=int(cfg_pg['maxconn']),
    database=cfg_pg['database'],
    user=cfg_pg['user'],
    password=cfg_pg['password'],
    host=cfg_pg['host'],
    port=int(cfg_pg['port']),
)

cfg_redis = config['redis']
redis = StrictRedis(connection_pool=BlockingConnectionPool(
    max_connections=int(cfg_redis['max_connections']),
    host=cfg_redis['host'],
    password=cfg_redis['password'],
    port=int(cfg_redis['port']),
    db=int(cfg_redis['db']),
))

fmt = logging.Formatter("[%(asctime)s] %(levelname)s: %(pathname)s:%(funcName)s(%(lineno)s): %(message)s")
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# stderr logging
sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)
sh.setFormatter(fmt)
logger.addHandler(sh)

