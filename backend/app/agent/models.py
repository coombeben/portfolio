from typing import Annotated, Literal

from neo4j import AsyncDriver
from pydantic import BaseModel, Field
from langchain.messages import AnyMessage, HumanMessage, AIMessage
from langgraph.graph import add_messages

from app.config import LLMConfig

AudienceMode = Literal['technical', 'non-technical']


# Structured output for the moderation node
class ModerationDecision(BaseModel):
    reasoning: str = Field(..., description="Internal explanation of your moderation decision. Be concise but clear. This will not be shown to the user.")
    allow: bool = Field(..., description="`true` if the message should be passed to the main chatbot. `false` if it should be blocked.")
    refusal_message: str | None = Field(None, description="A message shown to the user only when `allow` is `false`. Must be `null` when `allow` is `true`.")


class State(BaseModel):
    """State of the conversation between the user and the chatbot."""
    messages: Annotated[list[AnyMessage], add_messages]
    audience_mode: AudienceMode = 'technical'
    moderation_decision: ModerationDecision | None = None

    def to_moderator_inputs(self) -> HumanMessage:
        """Converts the state to a human message for the moderator."""
        message_content = ''
        for message in self.messages:
            if isinstance(message, HumanMessage):
                # Add full human messages to the moderator input
                message_content += f'<human>{message.content}</human>\n'
            elif isinstance(message, AIMessage):
                # Only show the first 50 characters of AI messages,
                # they're not all that important for moderation
                ai_content = message.content if len(message.content) <= 50 else f'{message.content[:50]}...'
                message_content += f'<assistant>{ai_content}</assistant>\n'
            # Ignore ToolMessages for moderation

        return HumanMessage(content=message_content)


class AgentContext(BaseModel):
    """Runtime context passed to LangGraph nodes and tools.

    Contains only what the agent needs during execution.
    Infrastructure concerns (checkpointer, connection strings) are not included.
    """
    model_config = {'arbitrary_types_allowed': True}

    # Used by nodes
    moderator_llm: LLMConfig
    chat_llm: LLMConfig
    enable_moderation: bool

    # Used by tools
    neo4j_driver: 'AsyncDriver'
