import os

import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv
from copilotkit import LangGraphAGUIAgent
from ag_ui_langgraph import add_langgraph_fastapi_endpoint

from agent import graph

load_dotenv()

app = FastAPI()

with postgres_conn():
    compiled_graph = graph.compile(postgres_conn)
    add_langgraph_fastapi_endpoint(
        app=app,
        agent=LangGraphAGUIAgent(
            name="Interactive portfolio",
            description="Describe your agent here, will be used for multi-agent orchestration",
            graph=compiled_graph,
        ),
        path="/agent",
    )


# add new route for health check
@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok"}


def main():
    """Run the uvicorn server."""
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "agent:app",
        host="0.0.0.0",
        port=port,
        reload=True,
    )
