from fastapi import FastAPI, Depends, Query
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from typing import List, Literal

from psycopg import Connection
import database as db

class Nimmy(BaseModel):
    title: str = Field(..., title="The name of the Nimmy", description="The title is used to identify a specific nimmy before getting into its details, ideal length is 128 or lesser", examples=["Do the math work in the morning after waking up", "Grocerry shopping", "Have to farm for flins in genshin impact"], max_length=128)

    content: str = Field(..., title="Give your Nimmy more details", description="The description can further be used to give the Nimmy more information, in 1024 or lesser characters", examples=["I have scored 80+ in maths, but now i want to go higher, I am targeting for 95 this time", "Mom has asked me to buy some things from the market, andI too have noticed lack of grocery in the home, so I better consider it before we start lacking", "Genshin just released it's brand new character Flins and I am damn impressed with its skills, I WANT IT NOWWWWWW"], max_length=1024)

    tags: List[str] = Field(default_factory=list, title="Tags make it easy to identify, search and sort Nimmies", description="Provide as many tags as you want in a list, or ommit this field if no tags are required for this Nimmy", examples=[['important', 'math'], ['important'], ['gaming', 'genshin', 'pulls']])


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.pool.open()

    with db.pool.connection() as conn:
        db.create_tables(conn)

    yield

    db.pool.close()


app = FastAPI(lifespan=lifespan)

@app.post('/nimmies', status_code=201)
def add_nimmy(nimmy: Nimmy, conn: Connection = Depends(db.get_db)):
    nimmy_id = db.add_nimmy(nimmy.title, nimmy.content, nimmy.tags, conn)
    return {'message': f"A Nimmy with an ID {nimmy_id} was added in the database"}

@app.get('/nimmies')
def list_nimmies(
    sort_by: Literal['id', 'title', 'time'] = Query(
        default='id', 
        title="Sort Nimmies", 
        description="Select whether the nimmies should be sorted, by what column if so",
        examples=['id', 'title', 'time']
    ),
    sort_order: Literal['asc', 'desc'] = Query(
        default='asc', 
        title="Order of sorting nimmies", 
        description="Change the order of sorting",
        examples=['asc', 'desc']
    ),
    status: Literal['all', 'is_deleted', 'is_archived', 'is_pinned'] = Query(
        default='all', 
        title="Filter the Nimmies",
        description="Choose whether you want all the data, only deleted, archived etc",
        examples=["all", "is_deleted", "is_archived", "is_pinned"]
    ),
    conn : Connection = Depends(db.get_db)
):
    
    return db.list_nimmies(sort_by, sort_order, status, conn)
