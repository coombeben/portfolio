"""
Centralised database connection management.
"""
from typing import Optional

from neo4j import GraphDatabase, Driver
from psycopg_pool import AsyncConnectionPool

from app.config import Config


class DatabaseManager:
    """Manages all database connections with proper lifecycle."""
    
    def __init__(self, config: Config):
        self.config = config
        self._neo4j_driver: Optional[Driver] = None
        self._pg_checkpointer: Optional[AsyncConnectionPool] = None
    
    async def connect(self) -> None:
        """Initialise all database connections."""
        # Setup Neo4j
        self._neo4j_driver = GraphDatabase.driver(
            self.config.neo4j_uri,
            auth=(self.config.neo4j_user, self.config.neo4j_password),
        )
        
        # Setup PostgreSQL checkpointer
        self._pg_checkpointer = AsyncConnectionPool(
            f"postgresql://{self.config.postgres_user}:{self.config.postgres_password}"
            f"@{self.config.postgres_uri}/{self.config.postgres_db}"
        )
    
    async def close(self) -> None:
        """Close all database connections."""
        if self._neo4j_driver:
            self._neo4j_driver.close()
        
        if self._pg_checkpointer:
            await self._pg_checkpointer.__aexit__(None, None, None)
    
    @property
    def neo4j_driver(self) -> Driver:
        """Get the Neo4j driver instance."""
        if not self._neo4j_driver:
            raise RuntimeError("Neo4j driver not initialised. Call connect() first.")
        return self._neo4j_driver
    
    @property
    def pg_checkpointer(self) -> AsyncConnectionPool:
        """Get the PostgreSQL checkpointer instance."""
        if not self._pg_checkpointer:
            raise RuntimeError("PostgreSQL checkpointer not initialised. Call connect() first.")
        return self._pg_checkpointer
