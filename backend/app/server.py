"""
The main FastAPI application.
"""
import logging
import warnings
from typing import TYPE_CHECKING

from pydantic.warnings import UnsupportedFieldAttributeWarning
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from neo4j.exceptions import DriverError
if TYPE_CHECKING:
    from redis.asyncio import Redis
    from neo4j import AsyncDriver

from app.config import settings
from app.dependencies import get_redis, get_neo4j_driver
from app.lifespan import lifespan
from app.routers import auth, chat

warnings.simplefilter("ignore", category=UnsupportedFieldAttributeWarning)
logger = logging.getLogger(__name__)

app = FastAPI(
    root_path='/api',
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)
app.include_router(auth.router)
app.include_router(chat.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.external_domain],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", include_in_schema=False)
async def health(
    redis: 'Redis' = Depends(get_redis),
    neo4j_driver: 'AsyncDriver' = Depends(get_neo4j_driver)
):
    """Health check. Confirms that Redis and Neo4j are both available."""
    try:
        await redis.ping()
        await neo4j_driver.verify_connectivity()
    except (ConnectionError, DriverError) as e:
        logger.error(e)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "error"},
        )

    return {"status": "ok"}
