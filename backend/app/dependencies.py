import hashlib
from typing import AsyncGenerator

from fastapi import Depends, Request, Response, HTTPException, status
from psycopg import AsyncConnection, sql
from psycopg_pool import AsyncConnectionPool
from neo4j import AsyncDriver

from app.config import settings


async def get_pg_conn(request: Request) -> AsyncGenerator[AsyncConnection, None]:
    pool: AsyncConnectionPool = request.app.state.pg_pool

    async with pool.connection() as conn:
        yield conn


async def get_neo4j_driver(request: Request) -> AsyncGenerator[AsyncDriver, None]:
    driver: AsyncDriver = request.app.state.neo4j_driver
    yield driver


def user_identifier(request: Request) -> str:
    """Returns a hashed identifier for the user based on their IP address."""
    user_ip = request.headers.get("X-Forwarded-For") or request.headers.get("X-Real-IP") or request.client.host
    hashed_ip = hashlib.sha256(user_ip.encode()).hexdigest()
    return hashed_ip


async def requires_auth(request: Request, response: Response, conn: AsyncConnection = Depends(get_pg_conn)) -> str:
    """Marks a route as requiring authentication."""
    session_id = request.cookies.get('session')
    if session_id is None:
        raise HTTPException(status_code=401, detail="Not logged in")

    result = await conn.execute("SELECT id FROM sessions WHERE id = %s", (session_id,))
    session = await result.fetchone()
    if session is None:
        response.delete_cookie('session')
        raise HTTPException(status_code=401, detail="Not logged in")

    return session_id


async def enforce_daily_quota(
        session_id: str = Depends(requires_auth),
        conn: AsyncConnection = Depends(get_pg_conn)
) -> None:
    query = sql.SQL("""
    INSERT INTO endpoint_usage (session_id, usage_date, message_count)
    VALUES (%s, CURRENT_DATE, 1)
    ON CONFLICT (session_id, usage_date)
    DO UPDATE SET message_count = endpoint_usage.message_count + 1
    RETURNING message_count
    """)

    result = await conn.execute(query, (session_id,))
    count, = await result.fetchone()
    if count > settings.daily_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily limit exceeded"
        )
