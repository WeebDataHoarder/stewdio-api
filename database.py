import config

import psycopg2

conn = psycopg2.connect(**config.postgres)
