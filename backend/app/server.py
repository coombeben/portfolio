from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from copilotkit import LangGraphAGUIAgent
from ag_ui.core.types import RunAgentInput
from ag_ui.encoder import EventEncoder

from app.mock_agent import graph
from app.config import get_config, AgentContext
from app.database import DatabaseManager

config = get_config('development')


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage database connections lifecycle."""
    # Setup all database connections
    db_manager = DatabaseManager(config)
    await db_manager.connect()

    context = AgentContext(
        moderator_llm=config.moderator_llm,
        chat_llm=config.chat_llm,
        enable_moderation=config.enable_moderation,
        neo4j_driver=db_manager.neo4j_driver,
    )

    # Create checkpointer on a dedicated long-lived connection
    checkpointer = AsyncPostgresSaver(db_manager.pg_conn)
    await checkpointer.setup()
    compiled_graph = graph.compile(checkpointer=checkpointer)
    agent = LangGraphAGUIAgent(
        name="langgraph-agent",
        graph=compiled_graph,
        config=context.to_langgraph_config(),
    )

    # Store on app state so request handlers can access it safely
    app.state.agent = agent

    try:
        yield
    finally:
        # Cleanup all connections
        await db_manager.close()


app = FastAPI(lifespan=lifespan)


@app.post('/')
async def langgraph_agent_endpoint(input_data: RunAgentInput, request: Request):
    # Get the accept header from the request
    accept_header = request.headers.get("accept")

    # Create an event encoder to properly format SSE events
    encoder = EventEncoder(accept=accept_header)

    async def event_generator():
        async for event in app.state.agent.run(input_data):
            yield encoder.encode(event)

    return StreamingResponse(
        event_generator(),
        media_type=encoder.get_content_type()
    )


@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok"}
