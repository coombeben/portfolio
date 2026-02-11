"use client";
import { useEffect, useMemo, useState } from "react";
import {
  CopilotChat,
  CopilotKitCSSProperties,
} from "@copilotkit/react-ui";
import { useRenderToolCall } from "@copilotkit/react-core";
import CustomMessages from "./components/messages";
import {CustomInput} from "./components/input";

const AUDIENCE_STORAGE_KEY = "portfolio-audience-mode";
const DAILY_LIMIT = 10;
const DAILY_USED = 3;

type AudienceMode = "technical" | "non-technical";

function ToolCallStatus({
  explanation,
  status,
}: {
  explanation: string;
  status: "inProgress" | "complete" | (string & {});
}) {
  const isInProgress = status === "inProgress";

  return (
    <div className="toolCallStatus" aria-live="polite">
      <div
        className="toolCallStatus__iconWrap"
        aria-hidden="true"
        title={isInProgress ? "In progress" : "Complete"}
      >
        {isInProgress ? (
          <span className="toolCallStatus__spinner" />
        ) : (
          <svg
            className="toolCallStatus__tick"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M4.89163 13.2687L9.16582 17.5427L18.7085 8"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        )}
      </div>
      <div className="toolCallStatus__text">
        <div className="toolCallStatus__label">{explanation}</div>
      </div>
    </div>
  );
}

export default function Page() {
  const [audienceMode, setAudienceMode] = useState<AudienceMode | null>(null);
  const [hasHydrated, setHasHydrated] = useState(false);

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

  useEffect(() => {
    setHasHydrated(true);
    const stored = window.localStorage.getItem(AUDIENCE_STORAGE_KEY);
    if (stored === "technical" || stored === "non-technical") {
      setAudienceMode(stored);
    }
  }, []);

  useEffect(() => {
    if (!hasHydrated) {
      return;
    }
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

  return (
    <main
      className="portfolioApp"
      data-modal-open={modalOpen ? "true" : "false"}
      style={
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
      <header className="appHeader">
        <div className="appHeader__brand">
          <div className="appHeader__logo" aria-hidden="true">
            BC
          </div>
          <div>
            <div className="appHeader__name">Ben Coombe</div>
            <div className="appHeader__tagline">Interactive Portfolio Chat</div>
          </div>
        </div>
        <a
          className="appHeader__link"
          href="https://github.com/your-name/your-repo"
          target="_blank"
          rel="noreferrer"
        >
          <span className="appHeader__linkIcon" aria-hidden="true">
            <svg viewBox="0 0 24 24" role="img">
              <path
                fill="currentColor"
                d="M12 2C6.477 2 2 6.655 2 12.402c0 4.59 2.865 8.484 6.839 9.86.5.095.682-.22.682-.495 0-.244-.01-1.05-.014-1.905-2.782.625-3.369-1.232-3.369-1.232-.455-1.204-1.11-1.525-1.11-1.525-.908-.648.068-.635.068-.635 1.003.074 1.532 1.07 1.532 1.07.892 1.59 2.341 1.131 2.913.864.09-.67.35-1.132.636-1.393-2.221-.264-4.556-1.154-4.556-5.138 0-1.136.39-2.064 1.03-2.792-.103-.262-.446-1.322.097-2.756 0 0 .84-.279 2.75 1.067A9.1 9.1 0 0 1 12 6.846c.826.004 1.66.115 2.438.335 1.909-1.346 2.748-1.067 2.748-1.067.545 1.434.202 2.494.1 2.756.64.728 1.028 1.656 1.028 2.792 0 3.994-2.34 4.87-4.57 5.129.359.324.679.961.679 1.939 0 1.4-.013 2.53-.013 2.875 0 .277.18.596.688.494C19.137 20.88 22 16.992 22 12.402 22 6.655 17.523 2 12 2Z"
              />
            </svg>
          </span>
          View Source
        </a>
      </header>

      <section className="chatShell" aria-hidden={modalOpen}>
        <CopilotChat
          // Messages={CustomMessages}
          Input={CustomInput}
          labels={{
            title: "Portfolio Assistant",
            initial: initialMessage,
            placeholder: "Ask me anything about Ben's work...",
          }}
        />
      </section>

      {modalOpen ? (
        <div className="audienceModal" role="dialog" aria-modal="true">
          <div className="audienceModal__backdrop" />
          <div className="audienceModal__card" role="document">
            <div className="audienceModal__eyebrow">Before we start</div>
            <h2 className="audienceModal__title">Select Audience Mode</h2>
            <p className="audienceModal__note">
              You can explore my work at your preferred technical depth.
            </p>
            <div className="audienceModal__options">
              <button
                className="audienceOption audienceOption--primary"
                onClick={() => handleSelectMode("technical")}
                type="button"
              >
                <div className="audienceOption__header">
                  <span className="audienceOption__title">
                    <span className="audienceOption__icon" aria-hidden="true" />
                    Technical
                  </span>
                  <span className="audienceOption__badge">Recommended</span>
                </div>
                <p>
                  For developers and engineers who want architecture decisions,
                  trade-offs, and implementation detail.
                </p>
              </button>
              <button
                className="audienceOption"
                onClick={() => handleSelectMode("non-technical")}
                type="button"
              >
                <div className="audienceOption__header">
                  <span className="audienceOption__title">
                    <span className="audienceOption__icon" aria-hidden="true" />
                    Non-Technical
                  </span>
                </div>
                <p>
                  For recruiters and managers who want outcomes, impact, and
                  clear high-level explanations.
                </p>
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
