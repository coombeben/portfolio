import uuid
from typing import Annotated

from pydantic import BaseModel
from langchain.tools import tool
from langchain.messages import AIMessage, AnyMessage, ToolMessage
from langgraph.prebuilt import ToolRuntime
from langgraph.graph import StateGraph, add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.runtime import Runtime

from app.config import AgentContext


class State(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]


@tool(parse_docstring=True)
def execute_cypher(cypher: str, explanation: str, runtime: ToolRuntime[AgentContext]) -> str:
    """Execute a Cypher query against the Neo4j database.

    Args:
        cypher (str): The Cypher query to execute.
        explanation (str): A short, user-facing explainer (a few words) that tells them what you're doing right now.
    """
    # Use the shared, pooled driver
    driver = runtime.context.neo4j_driver
    results = driver.execute_query(cypher)
    return '\n'.join((str(record) for record in results.records))


def chatbot(state: State, runtime: Runtime[AgentContext]) -> dict:
    """Creates cypher queries and responds to the user message."""
    tool_msg_exists = any(isinstance(msg, ToolMessage) for msg in state.messages)
    if tool_msg_exists:
        response = AIMessage(content='I called a tool, here\'s some information about that!')
    else:
        tool_call = {
            'name': 'execute_cypher',
            'args': {
                'cypher': 'MATCH (n) RETURN n LIMIT 10',
                'explanation': 'Finding the first 10 nodes'
            },
            'id': str(uuid.uuid4()),
            'type': 'tool_call'
        }
        response = AIMessage(content='', tool_calls=[tool_call])
    return {'messages': [response]}


tool_node = ToolNode([execute_cypher])

graph = (
    StateGraph(State, context_schema=AgentContext)
    .add_node('chatbot', chatbot)
    .add_node('tools', tool_node)
    .add_edge('__start__', 'chatbot')
    .add_conditional_edges('chatbot', tools_condition, ['tools', '__end__'])
    .add_edge('tools', 'chatbot')
)
