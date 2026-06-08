import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv
from os import getenv

load_dotenv()

DB_NAME = getenv("DB_NAME")
DB_USER = getenv("DB_USER")
DB_PASSWORD = getenv("DB_PASSWORD")
DB_HOST = getenv("DB_HOST")
DB_PORT = getenv("DB_PORT")

pool = ConnectionPool(
    conninfo=f"dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD} host={DB_HOST} port={DB_PORT}",
    kwargs={
        'row_factory': dict_row
    },
    min_size=2,
    max_size=10,
    open=False   
)

def get_db():
    with pool.connection() as conn:
        yield conn

#Get the tables done
def create_tables(conn: psycopg.Connection):
    with conn.cursor() as c:
        c.execute("""
                  CREATE TABLE IF NOT EXISTS nimmies(
                  id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                  title VARCHAR(128) UNIQUE NOT NULL,
                  content VARCHAR(1024) NOT NULL,
                  date_created TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                  date_updated TIMESTAMPTZ DEFAULT NULL,
                  is_pinned BOOLEAN DEFAULT FALSE,
                  status VARCHAR(16) NOT NULL DEFAULT 'active',
                  CONSTRAINT status_check CHECK(status IN ('active', 'archived', 'deleted')))
                  """)

        c.execute("""
                  CREATE TABLE IF NOT EXISTS tags(
                  id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                  name VARCHAR(64) UNIQUE NOT NULL)
                  """)
            
        c.execute("CREATE TABLE IF NOT EXISTS nimmytags (nimmy_id INTEGER references nimmies(id), tag_id INTEGER references tags(id), UNIQUE(nimmy_id, tag_id))")

#Tag related activities:

def link_tag(nimmy_id: int, tag: str, conn: psycopg.Connection):
    
    normalized_tag = tag.lower().strip()

    with conn.cursor() as c:
            c.execute(
                 """
                 INSERT INTO tags(name)
                 VALUES (%s)
                 ON CONFLICT (name) DO NOTHING
                 """,
                 (normalized_tag,)
            )

            c.execute(
                 """
                 SELECT id
                 FROM tags
                 WHERE name = %s
                 """,
                 (normalized_tag,)
            )

            tag_id = c.fetchone()['id']

            c.execute(
                 """
                 INSERT INTO nimmytags(nimmy_id, tag_id)
                 VALUES (%s, %s)
                 ON CONFLICT (nimmy_id, tag_id) DO NOTHING
                 """,
                 (nimmy_id, tag_id)
            )

            return {
                 'success': True,
                 'message': f"A tag was successfully linked to the nimmy with an id of {nimmy_id}",
                 'data': {
                      'tag_id': tag_id
                 }
            }
          

def unlink_tag(nimmy_id: int, tag_id: int, conn: psycopg.Connection):
    with conn.cursor() as c:
         c.execute(
              """
              DELETE FROM nimmytags
              WHERE nimmy_id = %s
              AND tag_id = %s
              """,
              (nimmy_id, tag_id)
         )
         return c.rowcount > 0
    
# state of the nimmy related activities

def pin_a_nimmy(nimmy_id: int, conn: psycopg.Connection):
     with conn.cursor() as c:
          c.execute(
               """
               UPDATE nimmies
               SET is_pinned = %s
               WHERE id = %s
               """,
               (True, nimmy_id)
          )
          return c.rowcount > 0
     
def change_status(nimmy_id: int, status: str, conn: psycopg.Connection):
     with conn.cursor() as c:
          c.execute(
               """
               UPDATE nimmies
               SET status = %s
               WHERE id = %s
               """,
               (status, nimmy_id)
          )
          return c.rowcount > 0
     
# Nimmy related activities

def add_a_nimmy(title: str, content: str, tags: list, conn: psycopg.Connection): 
     with conn.cursor() as c:
          c.execute(
               """
               INSERT INTO nimmies(title, content)
               VALUES (%s, %s)
               ON CONFLICT (title) DO NOTHING
               RETURNING id as nimmy_id
               """, 
               (title, content)
          )
          row = c.fetchone()

          if row is None:
               return {
                    'success': False,
                    'message': 'Title Already Exists',
                    'data': None
               }
          else:
               nimmy_id = row['nimmy_id']

          if not tags:
               return {
                    'success': True,
                    'message': 'Added Nimmy to the database without any tag',
                    'data': {
                         'nimmy_id': nimmy_id
                    }
               }
          
          tag_ids = []
          
          for tag in tags:
               tag_id = link_tag(nimmy_id, tag, conn)['data']['tag_id']

               tag_ids.append(tag_id)
          
          return {
               'success': True,
               'message': 'Added Nimmy to the database with given tags',
               'data': {
                    'nimmy_id': nimmy_id,
                    'tag_ids': tag_ids
               }
          }

def read_a_nimmy(nimmy_id: str, conn: psycopg.Connection):
     with conn.cursor() as c:
          c.execute(
               """
               SELECT
               n.id AS nimmy_id,
               n.title AS nimmy_title,
               n.content AS nimmy_content,
               COALESCE(
                    n.date_updated, n.date_created
               ) AS last_activity,
               COALESCE(
                    json_agg(
                         json_build_object(
                              'tag_id', t.id,
                              'tag_name', t.name
                         )
                    ) FILTER (WHERE t.id IS NOT NULL), '[]'::json
               ) AS nimmy_tags,
               n.status AS nimmy_status,
               n.is_pinned AS is_nimmy_pinned
               FROM nimmies AS n
               LEFT JOIN nimmytags
               ON n.id = nimmytags.nimmy_id
               LEFT JOIN tags AS t
               ON t.id = nimmytags.tag_id
               WHERE n.id = %s
               GROUP BY n.id
               """,
               (nimmy_id,)
          )

          return c.fetchone()
     
def list_nimmies(
          sort_by: str,
          sort_order: str,
          pinned_only: bool,
          status: str,
          contains_tag_id: int | None,
          search_by: str,
          conn: psycopg.Connection
):
     SORT_COLUMNS = {
          'id' : 'n.id',
          'title' : 'n.title',
          'last_activity': 'COALESCE(n.date_updated, n.date_created)'
     }

     filter_queries = []
     filter_values = []

     if status != 'all':
          filter_queries.append("n.status = %s")
          filter_values.append(status)
     
     if pinned_only:
          filter_queries.append("n.is_pinned = %s")
          filter_values.append(pinned_only)

     if contains_tag_id:
          filter_queries.append("n.id IN (SELECT nimmy_id FROM nimmytags WHERE tag_id = %s)")
          filter_values.append(contains_tag_id)

     if search_by:
          filter_queries.append("n.title ILIKE %s")
          filter_values.append(f"%{search_by}%")

     sql_query = f"""
               SELECT
               n.id AS nimmy_id,
               n.title AS nimmy_title,
               COALESCE(n.date_updated, n.date_created) AS last_activity,
               COALESCE(
                    json_agg(t.name) FILTER (WHERE t.id IS NOT NULL),
                    '[]'::json
               ) AS nimmy_tags,
               n.is_pinned AS is_nimmy_pinned
               FROM nimmies AS n
               LEFT JOIN nimmytags
               ON n.id = nimmytags.nimmy_id
               LEFT JOIN tags AS t
               ON t.id = nimmytags.tag_id 
               """
     if filter_queries:
          sql_query+= " WHERE " + " AND ".join(filter_queries)
     
     sql_query += f" GROUP BY n.id ORDER BY is_nimmy_pinned DESC, {SORT_COLUMNS[sort_by]} {sort_order}"

     with conn.cursor() as c:
          c.execute(
               sql_query,
               filter_values
          )
          return c.fetchall()

def edit_nimmy(
     nimmy_id : int,
     title: str,
     content: str,
     conn: psycopg.Connection
):
     edit_queries = []
     edit_values = []

     if title:
          edit_queries.append('n.title = %s')
          edit_values.append(title)
     
     if content:
          edit_queries.append('n.content = %s')
          edit_values.append(content)
     
     edit_queries.append('n.date_updated = NOW()')
     edit_values.append(nimmy_id)

     updates = ', '.join(edit_queries)

     with conn.cursor() as c:
          c.execute(
               f"""
               UPDATE nimmies
               SET {updates}
               WHERE n.id = %s
               """,
               (edit_values)
          )
          return c.rowcount > 0
     
def delete_nimmy(
     nimmy_id: int,
     conn: psycopg.Connection
):
     with conn.cursor() as c:
          c.execute(
               """
               DELETE FROM nimmies
               WHERE id = %s
               """,
               (nimmy_id,)
          )

          is_deleted = c.rowcount > 0

          c.execute(
               """
               DELETE from nimmytags
               WHERE nimmy_id = %s
               """,
               (nimmy_id,)
          )

          return is_deleted