from dotenv import load_dotenv
from langchain.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph

from backend.app.agent.graph import graph
from backend.app.agent.models import State
from backend.app.config import get_config

load_dotenv()


query = 'What resulted from the "Virtual analyst" project?'

inputs = State(messages=[HumanMessage(query)])
config = get_config('development')
events = []
agent: CompiledStateGraph = graph.compile()
for event in agent.stream(inputs, context=config, stream_mode='updates'):
    events.append(event)
    print(event)
