import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    // Allow presigned S3 URLs from any HTTPS host (storage bucket domain varies by provider)
    remotePatterns: [
      { protocol: "https", hostname: "**" },
    ],
  },
};

export default nextConfig;
