"""
This module defines the event types and structures used for the Agent User
Interaction Protocol. It includes an enumeration of event types, a base model
for events, and specific event models to capture details for each type of
interaction or operation in the protocol.
"""
from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field


class EventType(str, Enum):
    RUN_STARTED = "RUN_STARTED"
    RUN_FINISHED = "RUN_FINISHED"
    RUN_ERROR = "RUN_ERROR"
    TEXT_MESSAGE_START = "TEXT_MESSAGE_START"
    TEXT_MESSAGE_CONTENT = "TEXT_MESSAGE_CONTENT"
    TEXT_MESSAGE_END = "TEXT_MESSAGE_END"
    TOOL_CALL_START = "TOOL_CALL_START"
    TOOL_CALL_ARGS = "TOOL_CALL_ARGS"
    TOOL_CALL_END = "TOOL_CALL_END"
    TOOL_CALL_RESULT = "TOOL_CALL_RESULT"


class BaseEvent(BaseModel):
    """Base event for all events in the Agent User Interaction Protocol."""
    type: EventType
    timestamp: datetime = Field(default_factory=datetime.now)


class RunStartedEvent(BaseEvent):
    """Event indicating the start of a run."""
    type: EventType = EventType.RUN_STARTED
    run_id: str
    thread_id: str


class RunFinishedEvent(BaseEvent):
    """Event indicating the end of a run."""
    type: EventType = EventType.RUN_FINISHED
    run_id: str
    thread_id: str


class RunErrorEvent(BaseEvent):
    """Event indicating an error in a run."""
    type: EventType = EventType.RUN_ERROR
    run_id: str
    thread_id: str
    error_message: str


class TextMessageStartEvent(BaseEvent):
    """Event indicating the start of a text message."""
    type: EventType = EventType.TEXT_MESSAGE_START
    message_id: str


class TextMessageContentEvent(BaseEvent):
    """Event containing a piece of text message content."""
    type: EventType = EventType.TEXT_MESSAGE_CONTENT
    message_id: str
    delta: str = Field(min_length=1)


class TextMessageEndEvent(BaseEvent):
    """Event indicating the end of a text message."""
    type: EventType = EventType.TEXT_MESSAGE_END
    message_id: str


class ToolCallStartEvent(BaseEvent):
    """Event indicating the start of a tool call."""
    type: EventType = EventType.TOOL_CALL_START
    tool_call_id: str
    tool_call_name: str


class ToolCallArgsEvent(BaseEvent):
    """Event containing tool call arguments."""
    type: EventType = EventType.TOOL_CALL_ARGS
    tool_call_id: str
    delta: str = Field(min_length=1)


class ToolCallEndEvent(BaseEvent):
    """Event indicating the end of a tool call."""
    type: EventType = EventType.TOOL_CALL_END
    tool_call_id: str


class ToolCallResultEvent(BaseEvent):
    """Event containing the result of a tool call."""
    type: EventType = EventType.TOOL_CALL_RESULT
    tool_call_id: str
    message_id: str
    content: str
