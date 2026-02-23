"""
Provides functionality for creating and managing user sessions in a Redis store.
"""
import uuid
from datetime import date

from fastapi import HTTPException, status
from redis.asyncio import Redis

from app.config import settings


async def create_session(redis: Redis, hashed_ip: str) -> str:
    """Creates a new session for the given IP address."""
    today = date.today().isoformat()
    ip_sessions_key = f"ip_sessions:{hashed_ip}:{today}"

    # Atomically increment and get the daily session count for this IP
    count = await redis.incr(ip_sessions_key)
    if count == 1:
        # Set TTL on first creation so the key expires after the day
        await redis.expire(ip_sessions_key, 86400)

    if count > settings.max_sessions:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many sessions created today"
        )

    session_id = str(uuid.uuid4())
    session_key = f"session:{session_id}"

    await redis.hset(session_key, mapping={
        "identifier": hashed_ip,
        "created_at": today,
    })
    await redis.expire(session_key, settings.session_ttl)

    return session_id
