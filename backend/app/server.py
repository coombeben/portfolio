from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.mock_agent import graph
from app.config import get_config, AgentContext
from app.database import DatabaseManager
from app.encoder import SSEEventEncoder
from app.projector import AgentEventProjector, StreamInputs

config = get_config('development')


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage database connections lifecycle."""
    # Setup all database connections
    db_manager = DatabaseManager(config)
    await db_manager.connect()

    checkpointer = AsyncPostgresSaver(db_manager.pg_conn)
    await checkpointer.setup()

    agent = graph.compile(checkpointer=checkpointer)
    projector = AgentEventProjector(
        agent=agent,
        config=config.projection_config
    )

    # Store on app state so request handlers can access it safely
    app.state.projector = projector
    app.state.db_manager = db_manager

    try:
        yield
    finally:
        # Cleanup all connections
        await db_manager.close()


app = FastAPI(lifespan=lifespan)


@app.post('/')
async def langgraph_agent_endpoint(input_data: StreamInputs):
    encoder = SSEEventEncoder()

    context = AgentContext(
        moderator_llm=config.moderator_llm,
        chat_llm=config.chat_llm,
        enable_moderation=config.enable_moderation,
        neo4j_driver=app.state.db_manager.neo4j_driver,
    )

    async def event_generator():
        async for event in app.state.projector.astream(input_data, context=context):
            yield encoder.encode(event)

    return StreamingResponse(
        event_generator(),
        media_type=encoder.media_type
    )


@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok"}
