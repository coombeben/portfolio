import { useQuota } from "@/context/QuotaContext";


export function DailyLimitIndicator() {
  const { used, total } = useQuota();

  const diff = total - used;
  const remaining = (isNaN(diff) || diff < 0) ? "?" : Math.ceil(diff);

  return (
    <div className="dailyLimitIndicator">
      <span className="dailyLimitIndicator__text">
        {remaining} messages remaining today
      </span>
    </div>
  );
}