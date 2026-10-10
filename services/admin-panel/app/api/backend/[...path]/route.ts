import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { isSameOrigin } from "@/lib/origin";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  if (
    path[0] !== "v1" ||
    path.some((part) => part === "." || part === ".." || part.includes("/"))
  ) {
    return NextResponse.json({ detail: "Invalid API path" }, { status: 400 });
  }
  if (
    request.method !== "GET" &&
    !isSameOrigin(request)
  ) {
    return NextResponse.json(
      { detail: "Cross-origin request refused" },
      { status: 403 },
    );
  }
  const token = (await cookies()).get("propadmin-session")?.value;
  if (!token)
    return NextResponse.json(
      { detail: "Sign in to continue" },
      { status: 401 },
    );
  const upstream = new URL(
    `/${path.map(encodeURIComponent).join("/")}${request.nextUrl.search}`,
    process.env.API_BASE_URL ?? process.env.API_URL ?? "http://localhost:8000",
  );
  try {
    const result = await fetch(upstream, {
      method: request.method,
      headers: {
        Authorization: `Bearer ${token}`,
        ...(request.headers.get("last-event-id")
          ? { "Last-Event-ID": request.headers.get("last-event-id")! }
          : {}),
        "Content-Type":
          request.headers.get("content-type") ?? "application/json",
      },
      body: ["GET", "HEAD"].includes(request.method)
        ? undefined
        : await request.arrayBuffer(),
      cache: "no-store",
      signal: request.signal,
    });
    return new NextResponse(result.body, {
      status: result.status,
      headers: {
        "Content-Type":
          result.headers.get("content-type") ?? "application/json",
        "Cache-Control": "no-store",
        "X-Accel-Buffering": "no",
        ...(result.headers.get("content-disposition")
          ? {
              "Content-Disposition": result.headers.get("content-disposition")!,
            }
          : {}),
      },
    });
  } catch {
    return NextResponse.json(
      { detail: "API is unavailable. Check the local API service." },
      { status: 502 },
    );
  }
}
export {
  proxy as GET,
  proxy as POST,
  proxy as PATCH,
  proxy as DELETE,
  proxy as PUT,
};
