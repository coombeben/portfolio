import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // CORS issue prevention
  async rewrites() {
    return [
      {
        source: "/api/quota",
        destination: "http://localhost:8000/chat/quota",
      },
      {
        source: "/auth/session",
        destination: "http://localhost:8000/auth/session",
      },
      {
        source: "/auth/login",
        destination: "http://localhost:8000/auth/login",
      },
    ];
  },
};

export default nextConfig;
