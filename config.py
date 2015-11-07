import logging
from pathlib import Path
from psycopg2.pool import ThreadedConnectionPool
from redis import StrictRedis, BlockingConnectionPool

index_dir = Path(__file__).parent / "indexdir"
icecast_json = "http://127.0.0.1:8000/status-json.xsl"

postgres = ThreadedConnectionPool(
	minconn=1,
	maxconn=10,
	user="radio",
	database="music"
)

redis = StrictRedis(
	connection_pool=BlockingConnectionPool(
		max_connections=10
	)
)

fmt = logging.Formatter("[%(asctime)s] %(levelname)s: %(pathname)s:%(funcName)s(%(lineno)s): %(message)s")
logger = logging.getLogger("stewdio")
logger.setLevel(logging.DEBUG)

# stderr logging
sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)
sh.setFormatter(fmt)
logger.addHandler(sh)

