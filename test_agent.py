import asyncio
import sys
import uuid

from dotenv import load_dotenv
load_dotenv()

from langchain.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph

from backend.app.database import DatabaseManager
from backend.app.agent_wrapper import ProjectionConfig, StreamInputs, AgentEventProjector
from backend.app.agent.graph import graph
from backend.app.agent.models import State
from backend.app.config import get_config, AgentContext


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def pretty_print_event(event: dict) -> None:
    for node, update in event.items():
        if node == 'chatbot':
            message = update['messages'][-1]

            if message.text:
                print(f"Agent: {update['messages'][0].text}")
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    print(f"Tool: {tool_call['args']['explanation']}")


async def main(query: str) -> list:
    config = get_config('development')
    db_manager = DatabaseManager(config)
    await db_manager.connect()
    context = AgentContext(
        moderator_llm=config.moderator_llm,
        chat_llm=config.chat_llm,
        enable_moderation=config.enable_moderation,
        neo4j_driver=db_manager.neo4j_driver
    )
    agent: CompiledStateGraph = graph.compile()

    projector = AgentEventProjector(
        agent,
        ProjectionConfig(
            exclude_nodes={"moderator"},
            redact_tool_args={"execute_cypher": {"cypher"}},
            redact_tool_results={"execute_cypher"},
            redaction_text="[REDACTED]",
        )
    )
    inputs = State(messages=[HumanMessage(query)])
    stream_inputs = StreamInputs(state=inputs, run_id=uuid.uuid4().hex, thread_id=uuid.uuid4().hex)
    events = []
    for event in projector.stream(stream_inputs, context=context):
        events.append(event)
    return events


query = 'What resulted from the "Virtual analyst" project?'
events = asyncio.run(main(query))
