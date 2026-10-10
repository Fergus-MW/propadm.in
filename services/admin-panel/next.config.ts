import type { NextConfig } from "next";
import path from "node:path";
const workspaceRoot = path.resolve(process.cwd(), "../..");
const config: NextConfig = {
  output: "standalone",
  outputFileTracingRoot: workspaceRoot,
  turbopack: { root: workspaceRoot },
  poweredByHeader: false,
  agentRules: false,
};
export default config;
