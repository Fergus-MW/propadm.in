import type { NextRequest } from "next/server";

export function isSameOrigin(request: NextRequest): boolean {
  const origin = request.headers.get("origin");
  if (!origin) return true;
  // NextURL normalizes loopback IPs to localhost. Host retains the address
  // the browser actually requested, including the port.
  const expected = new URL(request.url);
  const host = request.headers.get("host");
  if (host) {
    // URL.host does not clear an existing port when the new host omits it.
    // Cloud Run's internal :3000 must not become part of the public origin.
    expected.port = "";
    expected.host = host;
  }
  return origin === expected.origin;
}
