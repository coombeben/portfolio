import logging
import secrets
import uuid
import warnings

from dotenv import load_dotenv

load_dotenv()

from pydantic import BaseModel
from pydantic.warnings import UnsupportedFieldAttributeWarning
from fastapi import FastAPI, Request, Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse
from ag_ui.core import RunAgentInput
from ag_ui.encoder import EventEncoder
from psycopg import AsyncConnection, sql
from psycopg.errors import OperationalError
from neo4j import AsyncDriver
from neo4j.exceptions import DriverError

# from app.mock_agent import State
from app.config import settings
from app.agent import AgentContext, State
from app.dependencies import get_pg_conn, get_neo4j_driver, user_identifier, requires_auth, enforce_daily_quota
from app.lifespan import lifespan
from app.projector import StreamInputs, agui_messages_to_langchain
from app.sessions import create_session

warnings.simplefilter("ignore", category=UnsupportedFieldAttributeWarning)
logger = logging.getLogger(__name__)


class Quota(BaseModel):
    remaining: int
    limit: int


class Login(BaseModel):
    password: str


app = FastAPI(lifespan=lifespan)


@app.post('/chat/stream')
async def langgraph_agent_endpoint(
        input_data: RunAgentInput,
        request: Request,
        neo4j_driver: AsyncDriver = Depends(get_neo4j_driver),
        _ = Depends(enforce_daily_quota)
) -> StreamingResponse:
    """Runs the agent and streams the events back to the client via AG-UI protocol"""
    accept_header = request.headers.get("accept")
    encoder = EventEncoder(accept=accept_header)

    # The existing state will automatically be recovered from Postgres
    # All we need is the latest message from the user.
    state = State(
        messages=agui_messages_to_langchain(input_data.messages)[-1:],
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
        async for event in app.state.projector.astream(stream_inputs, context=context):
            yield encoder.encode(event)

    return StreamingResponse(
        event_generator(),
        media_type=encoder.get_content_type()
    )


@app.get("/chat/quota")
async def quota(
    session_id: str = Depends(requires_auth),
    pg_conn: AsyncConnection = Depends(get_pg_conn)
) -> Quota:
    """Returns the user's remaining usage on the /chat/stream endpoint."""
    # As we (1) don't handle any untrusted user data and (2) Only use the DB for rate limiting,
    # an ORM would be overkill, so we just use good old-fashioned SQL queries here.
    query = sql.SQL("""
    SELECT message_count
    FROM endpoint_usage
    WHERE session_id = %s
      AND usage_date = CURRENT_DATE
    """)
    result = await pg_conn.execute(query, (session_id,))
    count = await result.fetchone()
    used = count[0] if count else 0
    daily_limit = settings.daily_limit

    return Quota(
        remaining=max(0, daily_limit - used),
        limit=daily_limit
    )


@app.post("/auth/login")
async def login(
    login: Login,
    response: Response,
    conn: AsyncConnection = Depends(get_pg_conn),
    identifier: str = Depends(user_identifier),
):
    """Logs in the user."""
    if not secrets.compare_digest('password'.encode('utf-8'), login.password.encode('utf-8')):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )

    session_id = await create_session(conn, identifier)

    response.set_cookie(
        'session',
        value=session_id,
        httponly=True,
        secure=True,
        samesite='lax',
        max_age=60 * 60 * 24 * 7
    )
    return {"message": "Login successful"}


@app.post("/auth/logout")
async def logout(response: Response):
    """Logs out the current user."""
    response.delete_cookie('session')
    return {"message": "Logout successful"}


@app.get("/auth/session")
async def session(_ = Depends(requires_auth)):
    """Determines if a session is valid.

    Returns 200 if the session cookie is present and valid.
    Else, 401
    """
    return {"message": "Session is valid"}


@app.get("/health", include_in_schema=False)
async def health(
    pg_conn: AsyncConnection = Depends(get_pg_conn),
    neo4j_driver: AsyncDriver = Depends(get_neo4j_driver)
):
    """Health check. Confirms that Postgres and Neo4j are both available."""
    try:
        await pg_conn.execute("SELECT 1")
        await neo4j_driver.verify_connectivity()
    except (OperationalError, DriverError) as e:
        logger.error(e)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "error"},
        )

    return {"status": "ok"}
