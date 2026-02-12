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
          // enableInspector={false}
          headers={{
            "Authorization": "Bearer my-secret-api"
          }}
        >
          {children}
        </CopilotKit>
      </body>
    </html>
  );
}