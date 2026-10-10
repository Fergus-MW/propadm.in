import type { NextRequest } from "next/server";

export function isSameOrigin(request: NextRequest): boolean {
  const origin = request.headers.get("origin");
  if (!origin) return true;
  // NextURL normalizes loopback IPs to localhost. Host retains the address
  // the browser actually requested, including the port.
  const expected = new URL(request.url);
  const host = request.headers.get("host");
  if (host) expected.host = host;
  return origin === expected.origin;
}
