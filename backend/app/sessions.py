import uuid

from fastapi import HTTPException, status
from psycopg import AsyncConnection, sql

from app.config import settings


async def create_session(conn: AsyncConnection, hashed_ip: str) -> str:
    count_daily_sessions = sql.SQL("""
    SELECT COUNT(*) 
    FROM sessions
    WHERE identifier = %s AND created_at::date = CURRENT_DATE
    """)
    result = await conn.execute(count_daily_sessions, (hashed_ip,))
    count, = await result.fetchone()
    if count >= settings.max_sessions:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many sessions created today"
        )

    session_id = str(uuid.uuid4())
    create_session_query = sql.SQL("""
    INSERT INTO sessions (id, identifier, expires_at) 
    VALUES (%s, %s, CURRENT_TIMESTAMP + INTERVAL '7 day')
    """)

    await conn.execute(create_session_query, (session_id, hashed_ip))
    return session_id
