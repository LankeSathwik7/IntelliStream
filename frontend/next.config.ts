import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Use 'export' for Cloudflare Pages static deployment
  // Change to 'standalone' for Docker deployment
  output: process.env.BUILD_TARGET === "docker" ? "standalone" : "export",

  // Disable image optimization for static export (use next/image with unoptimized)
  images: {
    unoptimized: true,
  },

  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  },

  // Trailing slashes for static export compatibility
  trailingSlash: true,
};

export default nextConfig;
