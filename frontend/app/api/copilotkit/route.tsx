import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { HttpAgent } from "@ag-ui/client";
import { NextRequest } from "next/server";

const serviceAdapter = new ExperimentalEmptyAdapter();

const agent = new HttpAgent({
  url: process.env.LANGGRAPH_DEPLOYMENT_URL || "http://localhost:8000/conversation",
  // headers: {
    // Authorization: `Bearer ${process.env.LANGGRAPH_DEPLOYMENT_API_KEY}`,
  // }
});

const runtime = new CopilotRuntime({
  agents: {
    // @ts-expect-error - The types for the agent are not fully defined, but it should still work at runtime.
    sample_agent: agent
  }
});

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};