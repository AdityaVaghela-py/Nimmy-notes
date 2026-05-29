import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv
import os

load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

pool = ConnectionPool(
    conninfo=f"dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD} host={DB_HOST} port={DB_PORT}",
    kwargs={"row_factory" : dict_row},
    min_size=2,
    max_size=10,
    open=False
)

def get_db():
    with pool.connection() as conn:
        yield conn

TABLE_NIMMIES = "nimmies"
TABLE_TAGS = 'tags'
TABLE_NIMMYTAGS = "nimmytags"

with pool:
    with pool.connection() as conn:
        with conn.cursor() as c:
            c.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE_NIMMIES}(
                  id SERIAL PRIMARY KEY,
                  title VARCHAR(128) NOT NULL,
                  content VARCHAR(1024) NOT NULL,
                  date_created TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                  date_updated TIMESTAMPTZ DEFAULT NULL,
                  is_archived BOOLEAN DEFAULT FALSE,
                  is_pinned BOOLEAN DEFAULT FALSE,
                  is_deleted BOOLEAN DEFAULT FALSE)""")

            c.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE_TAGS}(
                  id SERIAL PRIMARY KEY,
                  name VARCHAR(64) UNIQUE)""")
            
            c.execute(f"CREATE TABLE IF NOT EXISTS {TABLE_NIMMYTAGS}(nimmy_id INTEGER, tag_id INTEGER, UNIQUE(nimmy_id, tag_id))")

