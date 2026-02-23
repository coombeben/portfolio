"""
Basic authentication routes.
"""
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from redis.asyncio import Redis
from starlette import status
from starlette.responses import Response

from app.config import settings
from app.dependencies import get_redis, user_identifier, requires_auth
from app.sessions import create_session

router = APIRouter(
    prefix="/auth",
)


class Login(BaseModel):
    """Credentials for logging in."""
    password: str


class Message(BaseModel):
    """Simple message response."""
    message: str


@router.post("/login")
async def login(
    login_: Login,
    response: Response,
    redis: Redis = Depends(get_redis),
    identifier: str = Depends(user_identifier),
):
    """Logs in the user."""
    if not secrets.compare_digest(
        settings.app_password.encode('utf-8'),
        login_.password.encode('utf-8')
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )

    session_id = await create_session(redis, identifier)
    is_production = settings.environment == "production"

    response.set_cookie(
        'session',
        value=session_id,
        httponly=True,
        secure=is_production,
        samesite='lax' if not is_production else 'none',
        max_age=settings.session_ttl
    )
    return Message(message="Login successful")


@router.post("/logout")
async def logout(response: Response):
    """Logs out the current user."""
    response.delete_cookie('session')
    return Message(message="Logout successful")


@router.get("/session")
async def session(_ = Depends(requires_auth)):
    """Determines if a session is valid.

    Returns 200 if the session cookie is present and valid.
    Else, 401
    """
    return Message(message="Session is valid")
