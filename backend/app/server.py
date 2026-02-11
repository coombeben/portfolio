import uuid
import warnings
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from pydantic.warnings import UnsupportedFieldAttributeWarning
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from ag_ui.core import RunAgentInput
from ag_ui.encoder import EventEncoder

from app.mock_agent import graph, State
from app.config import get_config, AgentContext
from app.database import DatabaseManager
from app.projector import AgentEventProjector, StreamInputs, agui_messages_to_langchain

config = get_config('production')
warnings.simplefilter("ignore", category=UnsupportedFieldAttributeWarning)


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


@app.post('/conversation')
async def langgraph_agent_endpoint(input_data: RunAgentInput, request: Request):
    # Get the accept header from the request
    accept_header = request.headers.get("accept")

    # Create an event encoder to properly format SSE events
    encoder = EventEncoder(accept=accept_header)

    state = State(
        messages=agui_messages_to_langchain(input_data.messages),
    )
    stream_inputs = StreamInputs(
        state=state,
        run_id=str(uuid.uuid4()),
        thread_id=str(input_data.thread_id)
    )
    context = AgentContext(
        moderator_llm=config.moderator_llm,
        chat_llm=config.chat_llm,
        enable_moderation=config.enable_moderation,
        neo4j_driver=app.state.db_manager.neo4j_driver,
    )

    async def event_generator():
        async for event in app.state.projector.astream(stream_inputs, context=context):
            yield encoder.encode(event)

    return StreamingResponse(
        event_generator(),
        media_type=encoder.get_content_type()
    )


@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok"}
