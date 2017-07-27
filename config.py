import logging
from pathlib import Path
from psycopg2.pool import ThreadedConnectionPool
from redis import StrictRedis, BlockingConnectionPool

index_dir = Path(__file__).parent / "indexdir"

kawa_api = "http://127.0.0.1:4040/"

postgres = ThreadedConnectionPool(
	minconn=1,
	maxconn=10,
	user="radio",
	database="music",
	password="radio",
	host="127.0.0.1"
)

redis = StrictRedis(
	connection_pool=BlockingConnectionPool(
		max_connections=10
	)
)

fmt = logging.Formatter("[%(asctime)s] %(levelname)s: %(pathname)s:%(funcName)s(%(lineno)s): %(message)s")
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# stderr logging
sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)
sh.setFormatter(fmt)
logger.addHandler(sh)

