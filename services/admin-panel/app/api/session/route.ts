import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { isSameOrigin } from "@/lib/origin";
export async function GET() {
  return NextResponse.json({
    authenticated: Boolean((await cookies()).get("propadmin-session")?.value),
  });
}
export async function POST(request: NextRequest) {
  if (!isSameOrigin(request))
    return NextResponse.json(
      { detail: "Cross-origin request refused" },
      { status: 403 },
    );
  try {
    const payload = await request.json();
    const upstream = await fetch(
      `${process.env.API_BASE_URL ?? process.env.API_URL ?? "http://localhost:8000"}/v1/auth/login`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: payload.password }),
        cache: "no-store",
      },
    );
    const data = await upstream.json();
    if (!upstream.ok)
      return NextResponse.json(
        { detail: data.detail ?? "Unable to sign in" },
        { status: upstream.status },
      );
    if (!data.token)
      return NextResponse.json(
        { detail: "API did not return a session" },
        { status: 502 },
      );
    const result = NextResponse.json({ authenticated: true });
    result.cookies.set("propadmin-session", data.token, {
      httpOnly: true,
      secure: request.nextUrl.protocol === "https:",
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60 * 12,
    });
    return result;
  } catch {
    return NextResponse.json({ detail: "API is unavailable" }, { status: 502 });
  }
}
export async function DELETE(request: NextRequest) {
  if (!isSameOrigin(request))
    return NextResponse.json(
      { detail: "Cross-origin request refused" },
      { status: 403 },
    );
  const result = NextResponse.json({ authenticated: false });
  result.cookies.delete("propadmin-session");
  return result;
}
