import { NextRequest, NextResponse } from "next/server";
export const dynamic = "force-dynamic";
export async function GET(request: NextRequest) {
  const token = request.nextUrl.searchParams.get("token");
  if (
    !token ||
    !/^[A-Za-z0-9_-]+\.[a-f0-9]+$/.test(token) ||
    token.length > 2000
  )
    return NextResponse.json(
      { detail: "Invalid repair link" },
      { status: 401 },
    );
  try {
    const response = await fetch(
      new URL(
        "/v1/portal/shared",
        process.env.API_BASE_URL ??
          process.env.API_URL ??
          "http://localhost:8000",
      ),
      {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
        signal: request.signal,
      },
    );
    return new NextResponse(response.body, {
      status: response.status,
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "no-store",
        "Referrer-Policy": "no-referrer",
      },
    });
  } catch {
    return NextResponse.json(
      { detail: "Repair updates are temporarily unavailable" },
      { status: 502 },
    );
  }
}
