import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1:3000", "localhost:3000", "127.0.0.1", "localhost"],
  devIndicators: false,
};

export default nextConfig;
