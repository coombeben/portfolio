import uuid
import warnings

from dotenv import load_dotenv

load_dotenv()

from pydantic import BaseModel
from pydantic.warnings import UnsupportedFieldAttributeWarning
from fastapi import FastAPI, Request, Depends
from fastapi.responses import StreamingResponse
from ag_ui.core import RunAgentInput
from ag_ui.encoder import EventEncoder
from neo4j import AsyncDriver

from app.mock_agent import graph, State
from app.config import get_config, AgentContext
from app.dependencies import get_client_identifier, get_pg_conn, get_neo4j_driver
from app.lifespan import lifespan
from app.projector import AgentEventProjector, StreamInputs, agui_messages_to_langchain

config = get_config('production')
warnings.simplefilter("ignore", category=UnsupportedFieldAttributeWarning)


class Quota(BaseModel):
    remaining: int
    limit: int


app = FastAPI(lifespan=lifespan)


@app.post('/chat/stream')
async def langgraph_agent_endpoint(input_data: RunAgentInput, request: Request, neo4j_driver: AsyncDriver = Depends(get_neo4j_driver)):
    accept_header = request.headers.get("accept")
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
        neo4j_driver=neo4j_driver,
    )

    async def event_generator():
        async for event in app.state.projector.astream(stream_inputs, context=context):
            yield encoder.encode(event)

    return StreamingResponse(
        event_generator(),
        media_type=encoder.get_content_type()
    )


@app.get("/chat/quota")
async def quota(identifier: str = Depends(get_client_identifier), pg_conn=Depends(get_pg_conn)) -> Quota:
    """Returns the user's remaining usage on the /chat/stream endpoint."""
    # As we (1) don't handle any untrusted user data and (2) Only use the DB for rate limiting,
    # an ORM would be overkill, so we just use good old-fashioned SQL queries here.
    query = """
    SELECT request_count
    FROM endpoint_usage
    WHERE identifier = %s
    AND usage_date = CURRENT_DATE
    """
    result = await pg_conn.execute(query, (identifier,))
    count = await result.fetchone()
    used = count[0] if count else 0
    daily_limit = app.state.config.daily_limit

    return Quota(
        remaining=max(0, daily_limit - used),
        limit=daily_limit
    )


@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok"}
