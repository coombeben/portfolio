"""
Defines the lifespan management for a FastAPI application, providing setup and teardown
logic for database connections and application-level state orchestration.

This module configures and initialises connections to Neo4j and Redis, establishes a
checkpointer for LangGraph using Redis, and compiles an agent using application-specific
logic. These resources are attached to the FastAPI application's state for use during its
runtime and are properly closed when the application shuts down.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis
from neo4j import AsyncGraphDatabase
from langgraph.checkpoint.redis.aio import AsyncRedisSaver

from app.config import settings
from app.agent import graph
from app.projector import AgentEventProjector

__all__ = ['lifespan']


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Neo4j driver
    neo4j_driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )

    # Redis client
    redis_client = Redis.from_url(
        settings.redis_uri,
        password=settings.redis_password or None,
        decode_responses=True,
    )

    # LangGraph checkpointer
    async with AsyncRedisSaver(redis_client=redis_client, ttl=settings.ttl_config) as checkpointer:
        await checkpointer.asetup()

        agent = graph.compile(checkpointer=checkpointer)
        projector = AgentEventProjector(
            agent,
            settings.projection_config
        )

        app.state.projector = projector
        app.state.redis = redis_client
        app.state.neo4j_driver = neo4j_driver

        yield

    await redis_client.aclose()
    await neo4j_driver.close()
