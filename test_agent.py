from dotenv import load_dotenv
load_dotenv()

from langchain.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph

from backend.app.agent.graph import graph
from backend.app.agent.models import State
from backend.app.config import get_config

def pretty_print_event(event: dict) -> None:
    for node, update in event.items():
        if node == 'chatbot':
            message = update['messages'][-1]

            if message.text:
                print(f"Agent: {update['messages'][0].text}")
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    print(f"Tool: {tool_call['args']['explanation']}")


query = 'What resulted from the "Virtual analyst" project?'

inputs = State(messages=[HumanMessage(query)])
config = get_config('development')
events = []
agent: CompiledStateGraph = graph.compile()
for event in agent.stream(inputs, context=config, stream_mode='updates'):
    events.append(event)
    pretty_print_event(event)
