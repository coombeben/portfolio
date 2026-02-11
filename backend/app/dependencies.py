import uuid

from fastapi import Request, Response
from psycopg_pool import AsyncConnectionPool
from neo4j import AsyncDriver


async def get_pg_conn(request: Request):
    pool: AsyncConnectionPool = request.app.state.pg_pool

    async with pool.connection() as conn:
        yield conn


async def get_neo4j_driver(request: Request):
    driver: AsyncDriver = request.app.state.neo4j_driver

    async with driver.session() as session:
        yield session


def get_client_identifier(request: Request, response: Response) -> str:
    # 1. Prefer persistent cookie
    anon_id = request.cookies.get("anon_id")

    if anon_id:
        return anon_id

    # 2. Create new identifier
    new_id = str(uuid.uuid4())

    response.set_cookie(
        "anon_id",
        new_id,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30
    )

    return new_id
