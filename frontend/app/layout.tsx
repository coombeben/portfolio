import type { Metadata } from 'next'
import { AuthProvider } from "@/context/AuthContext";
import { CopilotKit } from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";
import "./globals.css";


export const metadata: Metadata = {
  title: 'Interactive Portfolio',
};

export default function RootLayout({ children }: {children: React.ReactNode}) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <CopilotKit
            runtimeUrl="/api/copilotkit"
            agent="agent"
            credentials="include"
            enableInspector={false}
          >
            {children}
          </CopilotKit>
        </AuthProvider>
      </body>
    </html>
  );
}