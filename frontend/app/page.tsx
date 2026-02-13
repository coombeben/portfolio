"use client";
import { useEffect, useMemo, useState } from "react";
import {
  CopilotChat,
  CopilotKitCSSProperties,
} from "@copilotkit/react-ui";

import { useRenderToolCall } from "@copilotkit/react-core";
import { Header } from "@/components/Header";
import {CustomInput} from "@/components/Input";
import {ToolCallStatus} from "@/components/ToolCallStatus";
import AudienceModal, { AudienceMode } from "@/components/AudienceModal";
import { QuotaProvider, useQuota } from "@/context/QuotaContext";
import LoginScreen from "@/components/LoginScreen";
import { useAuth } from "@/context/AuthContext";

const AUDIENCE_STORAGE_KEY = "portfolio-audience-mode";

function ChatInterface({ initialMessage, modalOpen }: { initialMessage: string, modalOpen: boolean }) {
  const { refreshQuota } = useQuota();

  useRenderToolCall({
    name: "execute_cypher",
    render: ({ args, status }) => {
      return (
        <ToolCallStatus
          explanation={args?.explanation ?? "Finding relevant projects..."}
          status={status}
        />
      );
    },
  });

  return (
    <section className="chatShell" aria-hidden={modalOpen}>
      <CopilotChat
        // Messages={CustomMessages}
        Input={CustomInput}
        onInProgress={async (inProgress) => {
          if (inProgress) {
            // Add a small delay before refreshing the quota to ensure the latest usage is reflected
            await new Promise(r => setTimeout(r, 500));
            await refreshQuota();
          }
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
  const [audienceMode, setAudienceMode] = useState<AudienceMode | null>(null);
  const [hasHydrated, setHasHydrated] = useState(false);

  useEffect(() => {
    setHasHydrated(true);

    const stored = window.localStorage.getItem(AUDIENCE_STORAGE_KEY);
    if (stored === "technical" || stored === "non-technical") {
      setAudienceMode(stored);
    }
  }, []);

  useEffect(() => {
    if (!hasHydrated) return;

    document.body.classList.toggle("modal-open", audienceMode === null);
  }, [audienceMode, hasHydrated]);

  const handleSelectMode = (mode: AudienceMode) => {
    window.localStorage.setItem(AUDIENCE_STORAGE_KEY, mode);
    setAudienceMode(mode);
  };

  const initialMessage = useMemo(() => {
    const baseMessage =
      "Hi! I'm here to give you insights into Ben's projects and technical decision-making. Feel free to ask about specific projects, technologies, challenges faced, or anything else you're curious about.";
    if (!audienceMode) {
      return baseMessage;
    }
    const modeLabel = audienceMode === "technical" ? "Technical" : "Non-technical";
    return `${baseMessage} (${modeLabel} mode)`;
  }, [audienceMode]);

  const modalOpen = hasHydrated && audienceMode === null;

  if (status === "checking") {
    return (
      <main className="portfolioApp">
        <Header />
        <div className="authScreen">
          <div className="authCard">
            <div className="authTitle">Checking session...</div>
          </div>
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
