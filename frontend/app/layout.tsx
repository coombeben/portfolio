import { CopilotKit } from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";
import "./globals.css";


export default function RootLayout({ children }: {children: React.ReactNode}) {
  return (
    <html lang="en">
      <body>
        <CopilotKit
            runtimeUrl="/api/copilotkit"
            agent="sample_agent"
            enableInspector={false}
        >
          {children}
        </CopilotKit>
      </body>
    </html>
  );
}