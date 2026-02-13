"""
Defines the lifespan management for a FastAPI application, providing setup and teardown
logic for database connections and application-level state orchestration.

This module configures and initialises connections to Neo4j and PostgreSQL databases,
establishes a checkpointer for PostgreSQL interactions, and compiles an agent using
application-specific logic. These resources are attached to the FastAPI application's
state for use during its runtime and are properly closed when the application shuts down.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from psycopg_pool import AsyncConnectionPool
from neo4j import AsyncGraphDatabase
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.config import settings
from app.mock_agent import graph
from app.projector import AgentEventProjector

__all__ = ['lifespan']


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Neo4j driver
    neo4j_driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )

    # Postgres pool
    dsn = (
        f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_uri}/{settings.postgres_db}"
    )
    pg_pool = AsyncConnectionPool(dsn, open=False)
    await pg_pool.open(wait=True)

    # Dedicated checkpointer connection
    async with pg_pool.connection() as conn:
        await conn.set_autocommit(True)

        checkpointer = AsyncPostgresSaver(conn)
        await checkpointer.setup()

        agent = graph.compile(checkpointer=checkpointer)
        projector = AgentEventProjector(
            agent,
            settings.projection_config
        )

        app.state.projector = projector
        app.state.pg_pool = pg_pool
        app.state.neo4j_driver = neo4j_driver

        yield

    await pg_pool.close()
    await neo4j_driver.close()
