import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // Pin the Turbopack workspace root to this directory. Without this, Next
  // infers the root by walking up for a lockfile/VCS root, which is wrong
  // here since `web/` is a subdirectory of the trendly repo (backend +
  // frontend share one repo, deployed as two separate Railway services).
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
