"use client";
import { useEffect, useMemo, useState } from "react";
import { CopilotChat, CopilotKitCSSProperties, } from "@copilotkit/react-ui";

import { useRenderToolCall, useCoAgent } from "@copilotkit/react-core";
import { Header } from "@/components/Header";
import {CustomInput} from "@/components/Input";
import {ToolCallStatus} from "@/components/ToolCallStatus";
import AudienceModal, { AudienceMode } from "@/components/AudienceModal";
import { QuotaProvider, useQuota } from "@/context/QuotaContext";
import LoginScreen from "@/components/LoginScreen";
import { useAuth } from "@/context/AuthContext";

const AUDIENCE_STORAGE_KEY = "portfolio-audience-mode";

type AgentState = {
  audience_mode: AudienceMode | null;
};

function ChatInterface({ initialMessage, modalOpen }: { initialMessage: string, modalOpen: boolean }) {
  const { refreshQuota } = useQuota();

  // Register our 3 tools with CopilotKit
  useRenderToolCall({
    name: "get_project_detail",
    render: ({ args, status }) => {
      // Defensive extraction with sensible fallbacks
      const projectIdRaw = args?.project_id;
      const projectId = typeof projectIdRaw === "string" ? projectIdRaw : "";
      let projectName = "Unknown Project";
      if (projectId) {
        const parts = projectId.split("-").slice(1);
        const cleaned = parts
          .map((word) =>
            word.length > 0
              ? word.charAt(0).toUpperCase() + word.slice(1)
              : ""
          )
          .filter(Boolean);
        projectName = cleaned.length > 0 ? cleaned.join(" ") : projectId;
      }

      const focus =
        args && args.focus != null && String(args.focus).trim().length > 0
          ? String(args.focus)
          : "details";

      const message = `Looking up ${focus} in project "${projectName}"`;

      return <ToolCallStatus message={message} status={status} />;
    },
  });

  useRenderToolCall({
    name: "search_knowledge_base",
    render: ({ args, status }) => {
      // Guard query and provide a general placeholder when missing
      const queryRaw = args?.query;
      const query =
        typeof queryRaw === "string" && queryRaw.trim().length > 0
          ? queryRaw.trim()
          : "general topics";

      const message = `Searching for projects related to "${query}"`;

      return <ToolCallStatus message={message} status={status} />;
    },
  });

  useRenderToolCall({
    name: "summarise_global_patterns",
    render: ({ args, status }) => {
      // Safe extraction of dimension and roles with defaults
      const dimensionRaw =
        typeof args?.dimension === "string" && args.dimension.length > 0
          ? args.dimension
          : "patterns";
      const dimension = dimensionRaw.toLowerCase();
      let message = `Analysing global ${dimension} patterns`;

      if (dimensionRaw.toUpperCase() === "TECHNOLOGY") {
        if (Array.isArray(args?.roles) && args.roles.length > 0) {
          const roleList = args.roles
            .map((r: unknown) => (r == null ? "" : String(r).trim()))
            .filter(Boolean)
            .join(", ");
          if (roleList) {
            message += ` specific to roles ${roleList}`;
          }
        }
      }

      return <ToolCallStatus message={message} status={status} />;
    },
  })

  return (
    <section className="chatShell" aria-hidden={modalOpen}>
      <CopilotChat
        Input={CustomInput}
        onInProgress={async (inProgress) => {
          // Add a small delay before refreshing the quota to ensure the latest usage is reflected
          const delay = inProgress ? 2000 : 0;
          await new Promise(r => setTimeout(r, delay));
          await refreshQuota();
        }}
        labels={{
          title: "Portfolio Assistant",
          initial: initialMessage,
          placeholder: "Ask me anything about Ben's work...",
        }}
      />
    </section>
  )
}


export default function Page() {
  const { status, isAuthenticated } = useAuth();
  const [hasHydrated, setHasHydrated] = useState(false);

  const { state , setState } = useCoAgent<AgentState>({
    name: "agent",
    initialState: {
      audience_mode: null
    }
  })

  // Hydration: runs once on mount, defers state updates via setTimeout
  // to satisfy react-hooks/set-state-in-effect
  useEffect(() => {
    const stored = window.localStorage.getItem(AUDIENCE_STORAGE_KEY);
    const validStored = stored === "technical" || stored === "non-technical" ? stored : null;

    setTimeout(() => {
      setHasHydrated(true);
      if (validStored) {
        setState({ audience_mode: validStored });
      }
    }, 0);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // setState intentionally omitted — not referentially stable

  // Effect: Toggle body class for modal
  useEffect(() => {
    if (!hasHydrated) return;
    document.body.classList.toggle("modal-open", state?.audience_mode === null);
  }, [state?.audience_mode, hasHydrated]);

  const handleSelectMode = (mode: AudienceMode) => {
    window.localStorage.setItem(AUDIENCE_STORAGE_KEY, mode);
    setState({ audience_mode: mode });
  };

  const modalOpen = hasHydrated && state?.audience_mode === null;

  const initialMessage = useMemo(() => {
    const baseMessage =
      "Hi! I'm here to give you insights into Ben's projects and technical decision-making. Feel free to ask about specific projects, technologies, challenges faced, or anything else you're curious about.";
    const mode = state?.audience_mode;
    if (!mode) {
      return baseMessage;
    }
    const modeLabel = mode === "technical" ? "Technical" : "Non-technical";
    return `${baseMessage} (${modeLabel} mode)`;
  }, [state?.audience_mode]);

  if (status === "checking") {
    return (
      <main className="portfolioApp">
        <Header />
        <div className="authScreen">
          <div className="authStatus">Checking session...</div>
        </div>
      </main>
    );
  }

  if (!isAuthenticated) {
    return (
      <main className="portfolioApp">
        <Header />
        <LoginScreen />
      </main>
    );
  }

  return (
    <QuotaProvider>
      <main
        className="portfolioApp"
        data-modal-open={modalOpen ? "true" : "false"}
        style=
          {
            {
              "--copilot-kit-primary-color": "#ef7b20",
              "--copilot-kit-contrast-color": "#ffffff",
              "--copilot-kit-background-color": "#fef8ee",
              "--copilot-kit-secondary-color": "#fdeed7",
              "--copilot-kit-secondary-contrast-color": "#40180a",
              "--copilot-kit-separator-color": "#fad9ae",
              "--copilot-kit-muted-color": "#f7be7a",
            } as CopilotKitCSSProperties
          }
      >
        <Header/>
        <ChatInterface initialMessage={initialMessage} modalOpen={modalOpen} />
        <AudienceModal open={modalOpen} onSelectMode={handleSelectMode}/>
      </main>
    </QuotaProvider>
  );
}

