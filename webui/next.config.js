/** @type {import('next').NextConfig} */
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:3006";

const nextConfig = {
  reactStrictMode: true,
  allowedDevOrigins: ["127.0.0.1"],
  images: { remotePatterns: [{ protocol: "https", hostname: "**" }] },
  async rewrites() {
    return [
      // Frontend calls relative /api/v1/...; proxy to the backend so there is
      // no CORS issue in dev. Set NEXT_PUBLIC_API_URL to point at your stack.
      { source: "/api/:path*", destination: `${API_URL}/api/:path*` },
    ];
  },
};

module.exports = nextConfig;
