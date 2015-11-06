from pathlib import Path
from psycopg2.pool import ThreadedConnectionPool
from redis import StrictRedis, BlockingConnectionPool

index_dir = Path(__file__).parent / "indexdir"

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
