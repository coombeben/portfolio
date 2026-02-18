export function ToolCallStatus({
  project_id,
  focus,
  status,
}: {
  project_id: string;
  focus: string[];
  status: "inProgress" | "complete" | (string & {});
}) {
  const isInProgress = status === "inProgress";
  const projectName = project_id
    .split('-')
    .slice(1)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
  const explanation = `Looking up ${focus.toString()} in project "${projectName}"`

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