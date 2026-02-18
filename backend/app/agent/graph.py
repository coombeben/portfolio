"""LangGraph agent definition."""
from typing import Literal

from langchain.messages import SystemMessage, AIMessage
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.runtime import Runtime

from .tools import get_project_detail
from .models import ModerationDecision, State, AgentContext
from .prompts import moderation_instructions, get_chatbot_prompt

__all__ = ['graph']


tools = [get_project_detail]


def moderator(state: State, runtime: Runtime[AgentContext]) -> dict:
    """Verify the content of the message."""
    messages = [
        SystemMessage(moderation_instructions),
        state.to_moderator_inputs()
    ]
    response: ModerationDecision = (
        runtime.context.moderator_llm
        .to_chat_model()
        .with_structured_output(ModerationDecision)
        .invoke(messages)
    )
    return {'moderation_decision': response}


def moderation_router(state: State) -> Literal['approved', 'rejected']:
    """Determine the next step in the conversation based on the moderation decision."""
    if state.moderation_decision.allow:
        return 'approved'
    return 'rejected'


def refusal(state: State) -> dict:
    """Returns a rejection message if the Moderator rejected the input."""
    refusal_message = state.moderation_decision.refusal_message
    if refusal_message is None:
        # Default refusal message if our Moderator LLM failed to provide one.
        refusal_message = "I'm sorry, I can't answer that."

    return {'messages': [AIMessage(content=refusal_message)]}


def chatbot(state: State, runtime: Runtime[AgentContext]) -> dict:
    """Creates cypher queries and responds to the user message."""
    messages = [
        SystemMessage(get_chatbot_prompt(state.audience_mode)),
        *state.messages,
    ]
    response = (
        runtime.context.chat_llm
        .to_chat_model()
        .bind_tools(tools)
        .invoke(messages)
    )
    return {'messages': [response]}


tool_node = ToolNode(tools)

graph = (
    StateGraph(State, context_schema=AgentContext)
    .add_node('moderator', moderator)
    .add_node('chatbot', chatbot)
    .add_node('refusal', refusal)
    .add_node('tools', tool_node)
    .add_edge('__start__', 'moderator')
    .add_conditional_edges('moderator', moderation_router, {'approved': 'chatbot', 'rejected': 'refusal'})
    .add_edge('refusal', '__end__')
    .add_conditional_edges('chatbot', tools_condition, ['tools', '__end__'])
    .add_edge('tools', 'chatbot')
)
