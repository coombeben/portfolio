from typing import Annotated, Literal

from pydantic import BaseModel, Field
from langchain.messages import AnyMessage, HumanMessage, AIMessage
from langgraph.graph import add_messages


AudienceMode = Literal['technical', 'non-technical']


# Structured output for the moderation node
class ModerationDecision(BaseModel):
    reasoning: str = Field(..., description="Internal explanation of your moderation decision. Be concise but clear. This will not be shown to the user.")
    allow: bool = Field(..., description="`true` if the message should be passed to the main chatbot. `false` if it should be blocked.")
    refusal_message: str | None = Field(None, description="A message shown to the user only when `allow` is `false`. Must be `null` when `allow` is `true`.")


# Internal state of the agent
class State(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]
    audience_mode: AudienceMode = 'technical'
    moderation_decision: ModerationDecision | None = None

    def to_moderator_inputs(self) -> HumanMessage:
        """Converts the state to a human message for the moderator."""
        message_content = ''
        for message in self.messages:
            if isinstance(message, HumanMessage):
                # Add full human messages to the moderator input
                message_content += f'Human: {message.content}\n'
            elif isinstance(message, AIMessage):
                # Only show the first 50 characters of AI messages,
                # they're not all that important for moderation
                ai_content = message.content if len(message.content) <= 50 else f'{message.content[:50]}...'
                message_content += f'AI: {ai_content}\n'
            # Ignore ToolMessages for moderation

        return HumanMessage(content=message_content)
