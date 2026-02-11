import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // CORS issue prevention
  async rewrites() {
    return [
      {
        source: "/api/quota",
        destination: "http://localhost:8000/chat/quota",
      },
    ];
  },
};

export default nextConfig;
