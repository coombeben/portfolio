import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { HttpAgent } from "@ag-ui/client";
import { NextRequest } from "next/server";

const serviceAdapter = new ExperimentalEmptyAdapter();

export const POST = async (req: NextRequest) => {

  const agent = new HttpAgent({
    url: process.env.LANGGRAPH_DEPLOYMENT_URL || "http://localhost:8000/chat/stream",
  });

  // We need to explicitly forward the cookies with each request for FastAPI auth
  const cookieHeader = req.headers.get("cookie");
  if (cookieHeader) {
    agent.headers = {
      ...agent.headers,
      cookie: cookieHeader,
    };
  }

  const runtime = new CopilotRuntime({
    agents: {
      // @ts-expect-error - The types for the agent are not fully defined, but it will still work at runtime.
      agent: agent
    }
  });

  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
    cors: {
      origin: "http://localhost:3000,http://localhost:8000",
      credentials: true,
  }
  });

  return handleRequest(req);
};
