"""
Custom implementation of LangGraphAGUIAgent
Allows context to be passed to the graph
"""
from copilotkit import LangGraphAGUIAgent
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from langgraph.typing import ContextT
from ag_ui_langgraph.agent import dump_json_safe
from ag_ui_langgraph.types import State, LangGraphEventTypes
from ag_ui_langgraph.utils import agui_messages_to_langchain, get_stream_payload_input
from ag_ui.core import (
    EventType,
    CustomEvent,
    RunAgentInput,
    RunFinishedEvent,
    RunStartedEvent,
)


class AGUIAgent(LangGraphAGUIAgent):
    def __init__(self, context: ContextT, *args, **kwargs):
        self.context = context
        super().__init__(*args, **kwargs)

    async def prepare_stream(self, input: RunAgentInput, agent_state: State, config: RunnableConfig):
        state_input = input.state or {}
        messages = input.messages or []
        forwarded_props = input.forwarded_props or {}
        thread_id = input.thread_id

        state_input["messages"] = agent_state.values.get("messages", [])
        self.active_run["current_graph_state"] = agent_state.values.copy()
        langchain_messages = agui_messages_to_langchain(messages)
        state = self.langgraph_default_merge_state(state_input, langchain_messages, input)
        self.active_run["current_graph_state"].update(state)
        config["configurable"]["thread_id"] = thread_id
        interrupts = agent_state.tasks[0].interrupts if agent_state.tasks and len(agent_state.tasks) > 0 else []
        has_active_interrupts = len(interrupts) > 0
        resume_input = forwarded_props.get('command', {}).get('resume', None)

        self.active_run["schema_keys"] = self.get_schema_keys(config)

        non_system_messages = [msg for msg in langchain_messages if not isinstance(msg, SystemMessage)]
        if len(agent_state.values.get("messages", [])) > len(non_system_messages):
            # Find the last user message by working backwards from the last message
            last_user_message = None
            for i in range(len(langchain_messages) - 1, -1, -1):
                if isinstance(langchain_messages[i], HumanMessage):
                    last_user_message = langchain_messages[i]
                    break

            if last_user_message:
                return await self.prepare_regenerate_stream(
                    input=input,
                    message_checkpoint=last_user_message,
                    config=config
                )

        events_to_dispatch = []
        if has_active_interrupts and not resume_input:
            events_to_dispatch.append(
                RunStartedEvent(type=EventType.RUN_STARTED, thread_id=thread_id, run_id=self.active_run["id"])
            )

            for interrupt in interrupts:
                events_to_dispatch.append(
                    CustomEvent(
                        type=EventType.CUSTOM,
                        name=LangGraphEventTypes.OnInterrupt.value,
                        value=dump_json_safe(interrupt.value),
                        raw_event=interrupt,
                    )
                )

            events_to_dispatch.append(
                RunFinishedEvent(type=EventType.RUN_FINISHED, thread_id=thread_id, run_id=self.active_run["id"])
            )
            return {
                "stream": None,
                "state": None,
                "config": None,
                "events_to_dispatch": events_to_dispatch,
            }

        if self.active_run["mode"] == "continue":
            await self.graph.aupdate_state(config, state, as_node=self.active_run.get("node_name"))

        if resume_input:
            stream_input = Command(resume=resume_input)
        else:
            payload_input = get_stream_payload_input(
                mode=self.active_run["mode"],
                state=state,
                schema_keys=self.active_run["schema_keys"],
            )
            stream_input = {**forwarded_props, **payload_input} if payload_input else None


        subgraphs_stream_enabled = input.forwarded_props.get('stream_subgraphs') if input.forwarded_props else False

        # Manual override: pass `context` arg
        kwargs = self.get_stream_kwargs(
            input=stream_input,
            config=config,
            subgraphs=bool(subgraphs_stream_enabled),
            version="v2",
            context=self.context,
        )

        stream = self.graph.astream_events(**kwargs)

        return {
            "stream": stream,
            "state": state,
            "config": config
        }

    async def prepare_regenerate_stream( # pylint: disable=too-many-arguments
            self,
            input: RunAgentInput,
            message_checkpoint: HumanMessage,
            config: RunnableConfig
    ):
        tools = input.tools or []
        thread_id = input.thread_id

        time_travel_checkpoint = await self.get_checkpoint_before_message(message_checkpoint.id, thread_id)
        if time_travel_checkpoint is None:
            return None

        fork = await self.graph.aupdate_state(
            time_travel_checkpoint.config,
            time_travel_checkpoint.values,
            as_node=time_travel_checkpoint.next[0] if time_travel_checkpoint.next else "__start__"
        )

        stream_input = self.langgraph_default_merge_state(time_travel_checkpoint.values, [message_checkpoint], input)
        subgraphs_stream_enabled = input.forwarded_props.get('stream_subgraphs') if input.forwarded_props else False

        # Manual override: pass `context` arg
        kwargs = self.get_stream_kwargs(
            input=stream_input,
            fork=fork,
            subgraphs=bool(subgraphs_stream_enabled),
            version="v2",
            context=self.context
        )
        stream = self.graph.astream_events(**kwargs)

        return {
            "stream": stream,
            "state": time_travel_checkpoint.values,
            "config": config
        }
