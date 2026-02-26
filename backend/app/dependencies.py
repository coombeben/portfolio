"""
Global FastAPI dependencies.
"""
import hmac
from datetime import date
from typing import AsyncGenerator

from fastapi import Depends, Request, Response, HTTPException, status
from redis.asyncio import Redis
from neo4j import AsyncDriver

from app.config import settings


async def get_redis(request: Request) -> AsyncGenerator[Redis, None]:
    """Returns a Redis client instance."""
    redis: Redis = request.app.state.redis
    yield redis


async def get_neo4j_driver(request: Request) -> AsyncGenerator[AsyncDriver, None]:
    """Returns a Neo4j driver instance."""
    driver: AsyncDriver = request.app.state.neo4j_driver
    yield driver


def user_identifier(request: Request) -> str:
    """Returns a hashed identifier for the user based on their IP address."""
    # As Uvicorn has the `--proxy-headers --forward-allow-ips *` args, we can use the
    # client.host to get the real IP address of the user, even behind proxies.
    ip = request.client.host
    hashed_ip = hmac.new(settings.secret_key.encode(), ip.encode(), "sha256").hexdigest()
    return hashed_ip


async def requires_auth(
    request: Request,
    response: Response,
    redis: Redis = Depends(get_redis)
) -> str:
    """Marks a route as requiring authentication."""
    session_id = request.cookies.get('session')
    if session_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in")

    exists = await redis.exists(f"session:{session_id}")
    if not exists:
        response.delete_cookie('session')
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in")

    return session_id


async def enforce_daily_quota(
        session_id: str = Depends(requires_auth),
        redis: Redis = Depends(get_redis)
) -> None:
    """Enforces a daily limit on the number of messages sent to the endpoint."""
    today = date.today().isoformat()
    quota_key = f"quota:{session_id}:{today}"

    count = await redis.incr(quota_key)
    if count == 1:
        # Expire at end of day: 24 h is a safe TTL
        await redis.expire(quota_key, 86400)

    if count > settings.daily_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily limit exceeded"
        )
