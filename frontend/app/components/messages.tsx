import { type AssistantMessageProps, type UserMessageProps, type MessagesProps } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";


export default function CustomMessages({ messages, inProgress, RenderMessage }: MessagesProps) {
  return (
    <div className="copilotKitMessages">
      {messages.map((message, index) => {
        const isCurrentMessage = index === messages.length - 1;
        return (
          <RenderMessage
            key={index}
            message={message}
            inProgress={inProgress}
            index={index}
            isCurrentMessage={isCurrentMessage}
          />
        );
      })}
    </div>
  );
}


// export const CustomUserMessage = (props: UserMessageProps) => {
//   const wrapperStyles = "flex items-center gap-2 justify-end mb-4";
//   const messageStyles = "bg-blue-500 text-white py-2 px-4 rounded-xl break-words flex-shrink-0 max-w-[80%]";
//   const avatarStyles = "bg-blue-500 shadow-sm min-h-10 min-w-10 rounded-full text-white flex items-center justify-center";
//
//   return (
//     <div className={wrapperStyles}>
//       <div className={messageStyles}>{props.message?.content}</div>
//       <div className={avatarStyles}>TS</div>
//     </div>
//   );
// };
//
// export const CustomAssistantMessage = (props: AssistantMessageProps) => {
//   const { icons } = useChatContext();
//   const { message, isLoading, subComponent } = props;
//
//   const avatarStyles = "bg-zinc-400 border-zinc-500 shadow-lg min-h-10 min-w-10 rounded-full text-white flex items-center justify-center";
//   const messageStyles = "px-4 rounded-xl pt-2";
//
//   const avatar = <div className={avatarStyles}><SparklesIcon className="h-6 w-6" /></div>
//
//   return (
//     <div className="py-2">
//       <div className="flex items-start">
//         {!subComponent && avatar}
//         <div className={messageStyles}>
//           {message && <Markdown content={message.content || ""} /> }
//           {isLoading && icons.spinnerIcon}
//         </div>
//       </div>
//       <div className="my-2">{subComponent}</div>
//     </div>
//   );
// };


// page.tsx
// import { CopilotChat,} from "@copilotkit/react-ui";
//
// <CopilotChat
//     UserMessage={CustomUserMessage}
//     AssistantMessage={CustomAssistantMessage}
// />