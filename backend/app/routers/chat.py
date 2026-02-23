import uuid
from datetime import date

from ag_ui.core import RunAgentInput
from ag_ui.encoder import EventEncoder
from fastapi import APIRouter, Depends
from neo4j import AsyncDriver
from pydantic import BaseModel
from redis.asyncio import Redis
from starlette.requests import Request
from starlette.responses import StreamingResponse

from app.agent import State, AgentContext
from app.config import settings
from app.dependencies import get_neo4j_driver, enforce_daily_quota, requires_auth, get_redis
from app.projector import agui_messages_to_langchain, StreamInputs

router = APIRouter(
    prefix="/chat",
)


class Quota(BaseModel):
    remaining: int
    limit: int


@router.post('/stream')
async def langgraph_agent_endpoint(
    input_data: RunAgentInput,
    request: Request,
    neo4j_driver: AsyncDriver = Depends(get_neo4j_driver),
    _ = Depends(enforce_daily_quota)
) -> StreamingResponse:
    """Runs the agent and streams the events back to the client via AG-UI protocol"""
    accept_header = request.headers.get("accept")
    encoder = EventEncoder(accept=accept_header)

    kwargs = {}
    if audience_mode := input_data.state.get("audience_mode"):
        kwargs["audience_mode"] = audience_mode

    state = State(
        # The existing message history will automatically be recovered from Redis
        # All we need is the latest message from the user.
        messages=agui_messages_to_langchain(input_data.messages)[-1:],
        **kwargs
    )
    stream_inputs = StreamInputs(
        state=state,
        run_id=str(uuid.uuid4()),
        thread_id=str(input_data.thread_id)
    )
    context = AgentContext(
        moderator_llm=settings.moderator_llm,
        chat_llm=settings.chat_llm,
        enable_moderation=settings.enable_moderation,
        neo4j_driver=neo4j_driver,
    )

    async def event_generator():
        async for event in request.app.state.projector.astream(stream_inputs, context=context):
            yield encoder.encode(event)

    return StreamingResponse(
        event_generator(),
        media_type=encoder.get_content_type()
    )


@router.get("/quota")
async def quota(
    session_id: str = Depends(requires_auth),
    redis: Redis = Depends(get_redis)
) -> Quota:
    """Returns the user's remaining usage on the /chat/stream endpoint."""
    today = date.today().isoformat()
    quota_key = f"quota:{session_id}:{today}"
    count = await redis.get(quota_key)
    used = int(count) if count else 0
    daily_limit = settings.daily_limit

    return Quota(
        remaining=max(0, daily_limit - used),
        limit=daily_limit
    )
