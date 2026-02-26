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
    url: (process.env.INTERNAL_API_BASE_URL || 'http://localhost') + "/api/chat/stream",
  });

  const clientIpHeaders = {
    'CF-Connecting-IP': req.headers.get('CF-Connecting-IP') || '',
  };

  // We need to explicitly forward the cookies with each request for FastAPI auth
  const cookieHeader = req.headers.get("cookie");
  if (cookieHeader) {
    agent.headers = {
      ...agent.headers,
      ...clientIpHeaders,
      cookie: cookieHeader,
    };
  }

  const runtime = new CopilotRuntime({
    agents: {
      // @ts-expect-error - The types for the agent are not fully defined, but it will still work at runtime.
      'agent': agent
    }
  });

  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
    cors: {
      origin: process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost',
      credentials: true,
  }
  });

  return handleRequest(req);
};
