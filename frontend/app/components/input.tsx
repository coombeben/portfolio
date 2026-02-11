import { type InputProps} from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";
import { DailyLimitIndicator } from "./DailyLimitIndicator";

export function CustomInput({ inProgress, onSend, onStop }: InputProps) {
  const handleSubmit = (value: string) => {
    if (value.trim()) onSend(value);
  };

  return (
    <div>
      <DailyLimitIndicator/>
      <div className="copilotKitInput">
        <textarea
          disabled={inProgress}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              handleSubmit(e.currentTarget.value);
              e.currentTarget.value = '';
            }
          }}
        />
        <div className="copilotKitInputControls">
          <div style={{flexGrow: 1}}/>
          <button
            className="copilotKitInputControlButton"
            aria-label="Send"
            disabled={inProgress}
            onClick={(e) => {
              const input = e.currentTarget.previousElementSibling as HTMLInputElement;
              handleSubmit(input.value);
              input.value = '';
            }}
          >
            <svg fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 19V5m0 0l-7 7m7-7l7 7"></path>
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
