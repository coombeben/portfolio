"""

"""
import json
from typing import Any, AsyncIterator, Iterable, Iterator, Optional

from pydantic import BaseModel, Field
from langgraph.graph.state import CompiledStateGraph

from .events import (
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
    ToolCallResultEvent
)


class StreamInputs(BaseModel):
    state: Any
    run_id: str
    thread_id: str


class ProjectionConfig(BaseModel):
    exclude_nodes: set[str] = Field(default_factory=set)
    redact_tool_args: dict[str, set[str]] = Field(default_factory=dict)
    redact_tool_results: set[str] = Field(default_factory=set)
    redaction_text: str = "[REDACTED]"


class AgentEventProjector:
    def __init__(self, agent: CompiledStateGraph, config: Optional[ProjectionConfig | dict] = None) -> None:
        """Initialize the projector with an agent and redaction config."""
        self._agent = agent
        self._config = self._normalize_config(config)

    def stream(self, inputs: StreamInputs, context: Any) -> Iterator[BaseEvent]:
        """Yield projected events from a synchronous agent stream."""
        text_started: set[str] = set()
        tool_started: set[str] = set()
        tool_args_emitted: set[str] = set()

        yield RunStartedEvent(run_id=inputs.run_id, thread_id=inputs.thread_id)
        try:
            for item in self._agent.stream(inputs.state, context=context, stream_mode="messages"):
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
                run_id=inputs.run_id,
                thread_id=inputs.thread_id,
                error_message=str(exc),
            )
            raise

    async def astream(self, inputs: StreamInputs, context: Any) -> AsyncIterator[BaseEvent]:
        """Yield projected events from an asynchronous agent stream."""
        text_started: set[str] = set()
        tool_started: set[str] = set()
        tool_args_emitted: set[str] = set()

        yield RunStartedEvent(run_id=inputs.run_id, thread_id=inputs.thread_id)
        try:
            async for item in self._agent.astream(inputs.state, context=context, stream_mode="messages"):
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
                run_id=inputs.run_id,
                thread_id=inputs.thread_id,
                error_message=str(exc),
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
    def _is_tool_message(message: Any) -> bool:
        """Return True when the message is a ToolMessage-like object."""
        return hasattr(message, "tool_call_id") and hasattr(message, "name")

    def _project_tool_message(self, message: Any) -> Optional[ToolCallResultEvent]:
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
        message: Any,
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

        if message_id and getattr(message, "chunk_position", None) == "last":
            if message_id in text_started:
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
    def _extract_text_delta(message: Any) -> str:
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
