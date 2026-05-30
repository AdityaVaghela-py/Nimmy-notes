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

def create_tables(conn: psycopg.Connection):
    with conn.cursor() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS nimmies(
                  id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                  title VARCHAR(128) NOT NULL,
                  content VARCHAR(1024) NOT NULL,
                  date_created TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                  date_updated TIMESTAMPTZ DEFAULT NULL,
                  is_archived BOOLEAN DEFAULT FALSE,
                  is_pinned BOOLEAN DEFAULT FALSE,
                  is_deleted BOOLEAN DEFAULT FALSE)""")

        c.execute("""CREATE TABLE IF NOT EXISTS tags(
                  id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                  name VARCHAR(64) UNIQUE)""")
            
        c.execute("CREATE TABLE IF NOT EXISTS nimmytags (nimmy_id INTEGER, tag_id INTEGER, UNIQUE(nimmy_id, tag_id))")

def add_nimmy(nimmy_title: str, nimmy_content: str, nimmy_tags: list, conn: psycopg.Connection):

    with conn.cursor() as c:

        c.execute('INSERT INTO nimmies (title, content) VALUES (%s, %s) RETURNING id AS nimmy_id', (nimmy_title, nimmy_content))
        nimmy_id = c.fetchone()['nimmy_id']

        if not nimmy_tags:
            return
        
        for tag in nimmy_tags:

            c.execute('SELECT id from tags WHERE name = %s', (tag,))
            row = c.fetchone()

            if row is not None:

                c.execute('INSERT into nimmytags (nimmy_id, tag_id) VALUES (%s, %s)', (nimmy_id, row['id']))

                continue
                
            c.execute('INSERT INTO tags (name) VALUES (%s) RETURNING id AS tag_id', (tag,))
            tag_id = c.fetchone()['tag_id']

            c.execute('INSERT into nimmytags (nimmy_id, tag_id) VALUES (%s, %s)', (nimmy_id, tag_id))