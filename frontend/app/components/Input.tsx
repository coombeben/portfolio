import { type InputProps} from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";
import { DailyLimitIndicator } from "./DailyLimitIndicator";
import { useRef, useEffect } from "react";
import { useQuota } from "@/context/QuotaContext";

export function CustomInput({ inProgress, onSend, onStop }: InputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { used, total } = useQuota();
  const diff = total - used;
  const remaining = Number.isNaN(diff) ? NaN : Math.ceil(diff);
  const isQuotaExhausted = remaining === 0;
  const isDisabled = inProgress || isQuotaExhausted;

  const autoResize = (textarea: HTMLTextAreaElement) => {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
  };

  useEffect(() => {
    if (textareaRef.current) {
      autoResize(textareaRef.current);
    }
  }, []);

  const handleSubmit = (value: string) => {
    if (isDisabled) {
      return;
    }
    if (value.trim()) {
      onSend(value);
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const placeholder = isQuotaExhausted ? "Daily limit reached" : "Ask me anything...";

  return (
    <div className="inputArea">
      <DailyLimitIndicator/>
      <div className={`copilotKitInput${isDisabled ? " copilotKitInput--disabled" : ""}`}>
        <textarea
          ref={textareaRef}
          disabled={isDisabled}
          placeholder={placeholder}
          onInput={(e) => autoResize(e.currentTarget)}
          onKeyDown={(e) => {
            if (isDisabled) {
              e.preventDefault();
              return;
            }
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e.currentTarget.value);
              e.currentTarget.value = '';
              autoResize(e.currentTarget);
            }
          }}
        />
        <div className="copilotKitInputControls">
          <div style={{flexGrow: 1}}/>
          <button
            className="copilotKitInputControlButton"
            aria-label="Send"
            disabled={isDisabled}
            onClick={(e) => {
              if (isDisabled) {
                return;
              }
              const textarea = e.currentTarget.parentElement?.previousElementSibling as HTMLTextAreaElement;
              if (textarea) {
                handleSubmit(textarea.value);
                textarea.value = '';
                autoResize(textarea);
              }
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
