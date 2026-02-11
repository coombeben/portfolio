import { useQuota } from "@/context/QuotaContext";


export function DailyLimitIndicator() {
  const { used, total } = useQuota();

  const percentage = (used / total) * 100;

  const getState = () => {
    if (used >= total) return 'limit';
    if (percentage >= 70) return 'warning';
    return 'normal';
  };

  const state = getState();

  return (
    <div className="dailyLimitIndicator" data-state={state}>
      <div className="dailyLimitIndicator__content">
        <div className="dailyLimitIndicator__text">
          <span className="dailyLimitIndicator__label">Daily usage</span>
          <span className="dailyLimitIndicator__value">
            {used} of {total} messages
          </span>
        </div>
        <div className="dailyLimitIndicator__bar">
          <div
            className="dailyLimitIndicator__fill"
            style={{ width: `${Math.min(percentage, 100)}%` }}
          />
        </div>
      </div>
      {state === 'limit' && (
        <div className="dailyLimitIndicator__message">
          Daily limit reached. Resets at midnight.
        </div>
      )}
      {state === 'warning' && (
        <div className="dailyLimitIndicator__message">
          Approaching your daily limit
        </div>
      )}
    </div>
  );
}

