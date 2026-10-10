import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export function GET() {
  // Only the public ingestion token is exposed; personal API keys stay server-side.
  const token = process.env.POSTHOG_PROJECT_TOKEN ?? "";
  return NextResponse.json(
    {
      projectToken: token.startsWith("phc_") ? token : "",
      host: process.env.POSTHOG_HOST ?? "https://us.i.posthog.com",
      environment: process.env.NODE_ENV === "production" ? "production" : "development",
    },
    { headers: { "Cache-Control": "no-store" } },
  );
}
