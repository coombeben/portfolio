"""
Centralised database connection management.
"""
from typing import Optional, Any

from neo4j import GraphDatabase, Driver
from psycopg_pool import AsyncConnectionPool

from app.config import Config


class DatabaseManager:
    """Manages all database connections with proper lifecycle."""

    def __init__(self, config: Config):
        self.config = config
        self._neo4j_driver: Optional[Driver] = None

        # Postgres
        self._pg_pool: Optional[AsyncConnectionPool] = None
        self._pg_conn: Any | None = None
        self._pg_conn_ctx: Any | None = None

    async def connect(self) -> None:
        """Initialise all database connections."""
        # Setup Neo4j
        self._neo4j_driver = GraphDatabase.driver(
            self.config.neo4j_uri,
            auth=(self.config.neo4j_user, self.config.neo4j_password),
        )

        # Setup PostgreSQL pool
        dsn = (
            f"postgresql://{self.config.postgres_user}:{self.config.postgres_password}"
            f"@{self.config.postgres_uri}/{self.config.postgres_db}"
        )
        self._pg_pool = AsyncConnectionPool(dsn, open=False)
        await self._pg_pool.open(wait=True)

        # Keep one dedicated connection for the checkpointer for the whole lifespan.
        self._pg_conn_ctx = self._pg_pool.connection()
        self._pg_conn = await self._pg_conn_ctx.__aenter__()

        # AsyncPostgresSaver requires autocommit to be enabled.
        await self._pg_conn.set_autocommit(True)

    async def close(self) -> None:
        """Close all database connections."""
        if self._neo4j_driver:
            self._neo4j_driver.close()

        if self._pg_conn_ctx is not None:
            await self._pg_conn_ctx.__aexit__(None, None, None)
            self._pg_conn_ctx = None
            self._pg_conn = None

        if self._pg_pool is not None:
            await self._pg_pool.close()
            self._pg_pool = None

    @property
    def neo4j_driver(self) -> Driver:
        """Get the Neo4j driver instance."""
        if not self._neo4j_driver:
            raise RuntimeError("Neo4j driver not initialised. Call connect() first.")
        return self._neo4j_driver

    @property
    def pg_conn(self):
        """Dedicated Postgres connection for the LangGraph checkpointer."""
        if self._pg_conn is None:
            raise RuntimeError("PostgreSQL connection not initialised. Call connect() first.")
        return self._pg_conn

    @property
    def pg_pool(self) -> AsyncConnectionPool:
        """Get the PostgreSQL pool instance."""
        if not self._pg_pool:
            raise RuntimeError("PostgreSQL pool not initialised. Call connect() first.")
        return self._pg_pool
