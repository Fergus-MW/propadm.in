import type { NextConfig } from "next";
import path from "node:path";
const workspaceRoot = path.resolve(process.cwd(), "../..");
const config: NextConfig = {
  output: "standalone",
  outputFileTracingRoot: workspaceRoot,
  turbopack: { root: workspaceRoot },
  allowedDevOrigins: ["127.0.0.1"],
  poweredByHeader: false,
  agentRules: false,
};
export default config;
