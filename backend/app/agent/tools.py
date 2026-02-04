"""
Tools for the LangGraph agent.
"""
from langchain.tools import tool
from langgraph.prebuilt import ToolRuntime

from app.config import AgentContext


# noinspection PyIncorrectDocstring
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
