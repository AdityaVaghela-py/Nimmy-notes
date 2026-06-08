from fastapi import FastAPI, Depends, Query, HTTPException
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

from psycopg import Connection
import db

class Nimmy(BaseModel):
    title: str = Field(
        ..., 
        title="The name of the Nimmy", 
        description="The title is used to identify a specific nimmy before getting into its details, ideal length is 128 or lesser", 
        examples=["Do the math work in the morning after waking up", "Grocerry shopping", "Have to farm for flins in genshin impact"], 
        max_length=128
    )

    content: str = Field(
        ..., 
        title="Give your Nimmy more details", 
        description="The description can further be used to give the Nimmy more information, in 1024 or lesser characters", 
        examples=["I have scored 80+ in maths, but now i want to go higher, I am targeting for 95 this time", "Mom has asked me to buy some things from the market, andI too have noticed lack of grocery in the home, so I better consider it before we start lacking", "Genshin just released it's brand new character Flins and I am damn impressed with its skills, I WANT IT NOWWWWWW"], 
        max_length=1024
    )

    tags: List[str] = Field(
        default_factory=list, 
        title="Tags make it easy to identify, search and sort Nimmies", 
        description="Provide as many tags as you want in a list, or ommit this field if no tags are required for this Nimmy", 
        examples=[['important', 'math'], ['important'], ['gaming', 'genshin', 'pulls']]
    )

class Tag(BaseModel):
    name : str = Field(
        ...,
        title="Tag of the nimmy",
        description="A tag is a term linking to a specific nimmy and further group more nimmies with eachother by a single tag, makes it easy to filter",
        examples=['python', 'programming language', 'gaming', 'important', 'imp'],
        max_length=32
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.pool.open()

    with db.pool.connection() as conn:
        db.create_tables(conn)

    yield

    db.pool.close()


app = FastAPI(lifespan=lifespan)

@app.post('/nimmies', status_code=201)
def add_nimmy(
    nimmy: Nimmy,
    conn: Connection = Depends(db.get_db)
):
    status = db.add_a_nimmy(
        title=nimmy.title,
        content=nimmy.content,
        tags=nimmy.tags,
        conn=conn
    )

    if not status['success']:
        raise HTTPException(
            status_code=409,
            detail=status
        )
    
    return status

@app.post('/nimmies/{nimmy_id}/tags', status_code=201)
def link_tag(nimmy_id: int, tag: Tag, conn: Connection = Depends(db.get_db)):

    status = db.link_tag(
        nimmy_id=nimmy_id,
        tag=tag.name,
        conn=conn
    )

    return status

@app.get('/nimmies')
def list_nimmies(
    sort_by: Literal['id', 'title', 'last_activity'] = Query(default='last_activity'),
    sort_order: Literal['asc', 'desc'] = Query(default='desc'),
    pinned_only: bool = Query(default=False),
    status: Literal['all', 'active', 'archived', 'deleted'] = Query(default='all'),
    contains_tag_id: int | None = Query(default=None),
    search_by: str = Query(default=None, max_length=128),
    conn: Connection = Depends(db.get_db)
):
    return db.list_nimmies(
        sort_by=sort_by,
        sort_order=sort_order,
        pinned_only=pinned_only,
        status=status,
        contains_tag_id=contains_tag_id,
        search_by=search_by,
        conn=conn
    )