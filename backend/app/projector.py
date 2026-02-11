"""
AgentEventProjector: A class to project LangGraph agent streams into a sequence of AG-UI protocol
events for UI consumption, with support for configurable redaction of sensitive information.
"""
import json
from typing import Any, AsyncIterator, Iterable, Iterator, Optional, Union

from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, ToolMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from ag_ui.core import (
    BaseEvent,
    RunStartedEvent,
    RunFinishedEvent,
    RunErrorEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    ToolCallStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    Message as AGUIMessage,
    TextInputContent,
    BinaryInputContent,
)

__all__ = [
    'StreamInputs',
    'ProjectionConfig',
    'agui_messages_to_langchain',
    'AgentEventProjector',
]


class StreamInputs(BaseModel):
    state: Any
    run_id: str
    thread_id: str


class ProjectionConfig(BaseModel):
    exclude_nodes: set[str] = Field(default_factory=set)
    redact_tool_args: dict[str, set[str]] = Field(default_factory=dict)
    redact_tool_results: set[str] = Field(default_factory=set)
    redaction_text: str = "[REDACTED]"


# Stolen from ag-ui-langgraph
def convert_agui_multimodal_to_langchain(content: list[TextInputContent | BinaryInputContent]) -> list[dict[str, Any]]:
    """Convert AG-UI multimodal content to LangChain's multimodal format."""
    langchain_content = []
    for item in content:
        if isinstance(item, TextInputContent):
            langchain_content.append({
                "type": "text",
                "text": item.text
            })
        elif isinstance(item, BinaryInputContent):
            # LangChain uses image_url format (OpenAI-style)
            content_dict = {"type": "image_url"}

            # Prioritize url, then data, then id
            if item.url:
                content_dict["image_url"] = {"url": item.url}
            elif item.data:
                # Construct data URL from base64 data
                content_dict["image_url"] = {"url": f"data:{item.mime_type};base64,{item.data}"}
            elif item.id:
                # Use id as a reference (some providers may support this)
                content_dict["image_url"] = {"url": item.id}

            langchain_content.append(content_dict)

    return langchain_content


# Stolen from ag-ui-langgraph
def agui_messages_to_langchain(messages: list[AGUIMessage]) -> list[BaseMessage]:
    langchain_messages = []
    for message in messages:
        role = message.role
        if role == "user":
            # Handle multimodal content
            if isinstance(message.content, str):
                content = message.content
            elif isinstance(message.content, list):
                content = convert_agui_multimodal_to_langchain(message.content)
            else:
                content = str(message.content)

            langchain_messages.append(HumanMessage(
                id=message.id,
                content=content,
                name=message.name,
            ))
        elif role == "assistant":
            tool_calls = []
            if hasattr(message, "tool_calls") and message.tool_calls:
                for tc in message.tool_calls:
                    tool_calls.append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "args": json.loads(tc.function.arguments) if hasattr(tc, "function") and tc.function.arguments else {},
                        "type": "tool_call",
                    })
            langchain_messages.append(AIMessage(
                id=message.id,
                content=message.content or "",
                tool_calls=tool_calls,
                name=message.name,
            ))
        elif role == "system":
            langchain_messages.append(SystemMessage(
                id=message.id,
                content=message.content,
                name=message.name,
            ))
        elif role == "tool":
            langchain_messages.append(ToolMessage(
                id=message.id,
                content=message.content,
                tool_call_id=message.tool_call_id,
            ))
        else:
            raise ValueError(f"Unsupported message role: {role}")
    return langchain_messages


class AgentEventProjector:
    def __init__(self, agent: CompiledStateGraph, config: Optional[ProjectionConfig | dict] = None) -> None:
        """Initialise the projector with an agent and redaction config."""
        self._agent = agent
        self._config = self._normalize_config(config)

    def stream(self, inputs: StreamInputs, context: Any) -> Iterator[BaseEvent]:
        """Yield projected events from a synchronous agent stream."""
        text_started: set[str] = set()
        tool_started: set[str] = set()
        tool_args_emitted: set[str] = set()

        config = RunnableConfig(
            run_id=inputs.run_id,
            configurable={
                'thread_id': inputs.thread_id
            }
        )

        yield RunStartedEvent(run_id=inputs.run_id, thread_id=inputs.thread_id)
        try:
            for item in self._agent.stream(inputs.state, config=config, context=context, stream_mode="messages"):
                message, meta = self._split_event(item)
                node = self._extract_node(meta)
                if node and node in self._config.exclude_nodes:
                    continue

                if self._is_tool_message(message):
                    event = self._project_tool_message(message)
                    if event is not None:
                        yield event
                    continue

                for event in self._project_ai_message(
                    message,
                    text_started,
                    tool_started,
                    tool_args_emitted,
                ):
                    yield event

            yield RunFinishedEvent(run_id=inputs.run_id, thread_id=inputs.thread_id)
        except Exception as exc:  # noqa: BLE001
            yield RunErrorEvent(
                message=str(exc),
            )
            raise

    async def astream(self, inputs: StreamInputs, context: Any) -> AsyncIterator[BaseEvent]:
        """Yield projected events from an asynchronous agent stream."""
        text_started: set[str] = set()
        tool_started: set[str] = set()
        tool_args_emitted: set[str] = set()

        config = RunnableConfig(
            run_id=inputs.run_id,
            configurable={
                'thread_id': inputs.thread_id
            }
        )

        yield RunStartedEvent(run_id=inputs.run_id, thread_id=inputs.thread_id)
        try:
            async for item in self._agent.astream(inputs.state, config=config, context=context, stream_mode="messages"):
                message, meta = self._split_event(item)
                node = self._extract_node(meta)
                if node and node in self._config.exclude_nodes:
                    continue

                if self._is_tool_message(message):
                    event = self._project_tool_message(message)
                    if event is not None:
                        yield event
                    continue

                for event in self._project_ai_message(
                    message,
                    text_started,
                    tool_started,
                    tool_args_emitted,
                ):
                    yield event

            yield RunFinishedEvent(run_id=inputs.run_id, thread_id=inputs.thread_id)
        except Exception as exc:  # noqa: BLE001
            yield RunErrorEvent(
                message=str(exc),
            )
            raise

    @staticmethod
    def _normalize_config(config: Optional[ProjectionConfig | dict]) -> ProjectionConfig:
        """Return a ProjectionConfig from an optional config object."""
        if config is None:
            return ProjectionConfig()
        if isinstance(config, ProjectionConfig):
            return config
        return ProjectionConfig(**config)

    @staticmethod
    def _split_event(item: Any) -> tuple[Any, dict[str, Any]]:
        """Split a stream item into message and metadata."""
        if isinstance(item, tuple) and len(item) == 2:
            message, meta = item
            return message, meta or {}
        return item, {}

    @staticmethod
    def _extract_node(meta: dict[str, Any]) -> Optional[str]:
        """Extract the node name from LangGraph metadata."""
        node = meta.get("langgraph_node")
        if node:
            return node
        checkpoint = meta.get("checkpoint_ns")
        if isinstance(checkpoint, str) and ":" in checkpoint:
            return checkpoint.split(":", 1)[0]
        return None

    @staticmethod
    def _is_tool_message(message: BaseMessage) -> bool:
        """Return True when the message is a ToolMessage-like object."""
        return hasattr(message, "tool_call_id") and hasattr(message, "name")

    def _project_tool_message(self, message: BaseMessage) -> Optional[ToolCallResultEvent]:
        """Convert a ToolMessage into a ToolCallResultEvent if possible."""
        tool_name = getattr(message, "name", None)
        tool_call_id = getattr(message, "tool_call_id", None)
        message_id = getattr(message, "id", None)
        content = getattr(message, "content", "")

        if tool_name in self._config.redact_tool_results:
            content = self._config.redaction_text

        if not tool_call_id or not message_id:
            return None

        return ToolCallResultEvent(
            tool_call_id=tool_call_id,
            message_id=message_id,
            content=str(content),
        )

    def _project_ai_message(
        self,
        message: BaseMessage,
        text_started: set[str],
        tool_started: set[str],
        tool_args_emitted: set[str],
    ) -> Iterable[BaseEvent]:
        """Convert an AIMessage-like chunk into protocol events."""
        events: list[BaseEvent] = []

        message_id = getattr(message, "id", None)
        delta = self._extract_text_delta(message)
        if message_id and delta:
            if message_id not in text_started:
                text_started.add(message_id)
                events.append(TextMessageStartEvent(message_id=message_id))
            events.append(TextMessageContentEvent(message_id=message_id, delta=delta))

        # Emit end-of-text for chunked streams (AIMessageChunk) AND full messages (AIMessage).
        if message_id:
            is_chunk = isinstance(message, AIMessageChunk)
            is_full = isinstance(message, AIMessage)

            should_end = (
                (is_chunk and getattr(message, "chunk_position", None) == "last")
                or (is_full and not is_chunk)
            )
            if should_end and message_id in text_started:
                events.append(TextMessageEndEvent(message_id=message_id))

        tool_call_chunks = getattr(message, "tool_call_chunks", None) or []
        tool_calls = getattr(message, "tool_calls", None) or []

        for chunk in tool_call_chunks:
            tool_call_id = chunk.get("id") if isinstance(chunk, dict) else None
            tool_name = chunk.get("name") if isinstance(chunk, dict) else None
            if not tool_call_id or not tool_name:
                continue

            if self._should_skip_tool_args(tool_name):
                continue

            if tool_call_id not in tool_started:
                tool_started.add(tool_call_id)
                events.append(ToolCallStartEvent(tool_call_id=tool_call_id, tool_call_name=tool_name))

            delta = chunk.get("args", "") if isinstance(chunk, dict) else ""
            if delta:
                tool_args_emitted.add(tool_call_id)
                events.append(ToolCallArgsEvent(tool_call_id=tool_call_id, delta=delta))

        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue
            tool_name = tool_call.get("name")
            tool_call_id = tool_call.get("id")
            args = tool_call.get("args")

            if not tool_name or not tool_call_id:
                continue

            if tool_call_id not in tool_started:
                tool_started.add(tool_call_id)
                events.append(ToolCallStartEvent(tool_call_id=tool_call_id, tool_call_name=tool_name))

            if tool_call_id not in tool_args_emitted:
                args_delta = self._format_tool_args(tool_name, args)
                if args_delta:
                    events.append(ToolCallArgsEvent(tool_call_id=tool_call_id, delta=args_delta))

            events.append(ToolCallEndEvent(tool_call_id=tool_call_id))

        return events

    @staticmethod
    def _extract_text_delta(message: BaseMessage) -> str:
        """Extract text delta from model message content."""
        content = getattr(message, "content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    if item.get("type") == "text" and isinstance(item.get("text"), str):
                        parts.append(item["text"])
            return "".join(parts)
        return ""

    def _should_skip_tool_args(self, tool_name: Optional[str]) -> bool:
        """Return True when tool arg chunks should be suppressed."""
        if not tool_name:
            return False
        return tool_name in self._config.redact_tool_args

    def _format_tool_args(self, tool_name: Optional[str], args: Any) -> str:
        """Serialize tool args with redactions applied."""
        if tool_name and tool_name in self._config.redact_tool_args:
            redacted_keys = self._config.redact_tool_args.get(tool_name, set())
            if "*" in redacted_keys:
                return json.dumps({"redacted": self._config.redaction_text})

            if isinstance(args, dict):
                sanitized = dict(args)
                for key in redacted_keys:
                    if key in sanitized:
                        sanitized[key] = self._config.redaction_text
                return json.dumps(sanitized)

            return json.dumps({"redacted": self._config.redaction_text})

        if isinstance(args, dict):
            return json.dumps(args)
        if isinstance(args, str):
            return args
        return ""
