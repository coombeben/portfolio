from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager

from fastapi import FastAPI
from ag_ui_langgraph import add_langgraph_fastapi_endpoint
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.agui_agent import AGUIAgent
from app.agent import graph
from app.config import get_config, AgentContext
from app.database import DatabaseManager


# Global state managed in lifespan
db_manager: DatabaseManager | None = None
context: AgentContext | None = None
compiled_graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage database connections lifecycle."""
    global db_manager, context, compiled_graph
    
    # Initialise config
    config = get_config('development')

    # Setup all database connections
    db_manager = DatabaseManager(config)
    await db_manager.connect()

    # Create the context
    context = AgentContext(
        moderator_llm=config.moderator_llm,
        chat_llm=config.chat_llm,
        enable_moderation=config.enable_moderation,
        neo4j_driver=db_manager.neo4j_driver
    )
    # Compile graph with PostgreSQL checkpointer
    async with db_manager.pg_checkpointer.connection() as conn:
        checkpointer = AsyncPostgresSaver(conn)
        await checkpointer.setup()
        compiled_graph = graph.compile(checkpointer=checkpointer)
    
    yield
    
    # Cleanup all connections
    await db_manager.close()


app = FastAPI(lifespan=lifespan)

add_langgraph_fastapi_endpoint(
    app=app,
    agent=AGUIAgent(
        name="Interactive portfolio",
        graph=compiled_graph,
        context=context
    ),
    path="/",
)


@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok"}
