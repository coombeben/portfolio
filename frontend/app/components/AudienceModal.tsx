import React from "react";

export type AudienceMode = "technical" | "non-technical";

interface AudienceModalProps {
  open: boolean;
  onSelectMode: (mode: AudienceMode) => void;
}

export default function AudienceModal({
  open,
  onSelectMode,
}: AudienceModalProps) {
  if (!open) return null;

  return (
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
            onClick={() => onSelectMode("technical")}
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
            onClick={() => onSelectMode("non-technical")}
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
  );
}
