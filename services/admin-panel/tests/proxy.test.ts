import { beforeEach, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
const cookie = vi.hoisted(() => ({
  value: "test-session-token" as string | undefined,
}));
vi.mock("next/headers", () => ({
  cookies: async () => ({
    get: () => (cookie.value ? { value: cookie.value } : undefined),
  }),
}));
import { GET, PATCH } from "@/app/api/backend/[...path]/route";
import { POST as login, DELETE as logout } from "@/app/api/session/route";
beforeEach(() => {
  cookie.value = "test-session-token";
  vi.unstubAllGlobals();
});
it("accepts loopback login, logout and writes while rejecting other origins", async () => {
  const fetch = vi.fn().mockImplementation(async () =>
    new Response(JSON.stringify({ token: "test-login-token" })),
  );
  vi.stubGlobal("fetch", fetch);
  const headers = {
    host: "127.0.0.1:3000",
    origin: "http://127.0.0.1:3000",
    "Content-Type": "application/json",
  };
  expect((await login(new NextRequest("http://127.0.0.1:3000/api/session", {
    method: "POST", headers, body: JSON.stringify({ password: "test-password" }),
  }))).status).toBe(200);
  expect((await logout(new NextRequest("http://127.0.0.1:3000/api/session", {
    method: "DELETE", headers,
  }))).status).toBe(200);
  const context = { params: Promise.resolve({ path: ["v1", "entities", "a"] }) };
  expect((await PATCH(new NextRequest("http://127.0.0.1:3000/api/backend/v1/entities/a", {
    method: "PATCH", headers, body: "{}",
  }), context)).status).toBe(200);
  fetch.mockClear();
  for (const origin of ["http://localhost:3000", "http://127.0.0.1:3001", "https://other.example", "null"]) {
    const request = new NextRequest("http://127.0.0.1:3000/api/session", {
      method: "POST", headers: { ...headers, origin, "x-forwarded-host": origin },
      body: "{}",
    });
    expect((await login(request)).status).toBe(403);
  }
  expect(fetch).not.toHaveBeenCalled();
});
it("refuses anonymous API reads and cross-origin mutations", async () => {
  const fetch = vi.fn();
  vi.stubGlobal("fetch", fetch);
  cookie.value = undefined;
  const anonymous = await GET(
    new NextRequest("http://localhost:3000/api/backend/v1/entities"),
    { params: Promise.resolve({ path: ["v1", "entities"] }) },
  );
  expect(anonymous.status).toBe(401);
  cookie.value = "test-session-token";
  const cross = await PATCH(
    new NextRequest("http://localhost:3000/api/backend/v1/entities/a", {
      method: "PATCH",
      headers: { origin: "https://other.example" },
    }),
    { params: Promise.resolve({ path: ["v1", "entities", "a"] }) },
  );
  expect(cross.status).toBe(403);
  expect(fetch).not.toHaveBeenCalled();
});
it("uses the public host and port behind the production proxy", async () => {
  const fetch = vi.fn().mockImplementation(async () =>
    new Response(JSON.stringify({ token: "test-login-token" })),
  );
  vi.stubGlobal("fetch", fetch);
  for (const host of [
    "admin-panel-tnzhas3sga-ew.a.run.app",
    "admin-panel-309727281538.europe-west1.run.app",
  ]) {
    const headers = {
      host,
      origin: `https://${host}`,
      "Content-Type": "application/json",
      "x-forwarded-proto": "https",
    };
    const request = (method: string, origin = headers.origin) =>
      new NextRequest("https://0.0.0.0:3000/api/session", {
        method,
        headers: { ...headers, origin },
        ...(["POST", "PATCH"].includes(method)
          ? { body: JSON.stringify({ password: "test-password" }) }
          : {}),
      });
    const result = await login(request("POST"));
    expect(result.status).toBe(200);
    expect(result.cookies.get("propadmin-session")).toMatchObject({
      httpOnly: true, secure: true, sameSite: "lax",
    });
    expect((await logout(request("DELETE"))).status).toBe(200);
    const context = { params: Promise.resolve({ path: ["v1", "entities", "a"] }) };
    expect((await PATCH(request("PATCH"), context)).status).toBe(200);
    fetch.mockClear();
    for (const origin of [
      `https://${host}:3000`, `http://${host}`, "https://other.example", "null",
    ]) {
      expect((await login(request("POST", origin))).status).toBe(403);
      expect((await logout(request("DELETE", origin))).status).toBe(403);
      expect((await PATCH(request("PATCH", origin), context)).status).toBe(403);
    }
    expect(fetch).not.toHaveBeenCalled();
  }
});
it("forwards cookie authentication and streams without returning tokens", async () => {
  const fetch = vi.fn().mockResolvedValue(
    new Response('event: delta\ndata: {"version":2}\n\n', {
      headers: { "Content-Type": "text/event-stream" },
    }),
  );
  vi.stubGlobal("fetch", fetch);
  const result = await GET(
    new NextRequest(
      "http://localhost:3000/api/backend/v1/entities/graph/stream?since=1",
      { headers: { "Last-Event-ID": "7" } },
    ),
    {
      params: Promise.resolve({ path: ["v1", "entities", "graph", "stream"] }),
    },
  );
  expect(fetch.mock.calls[0][1].headers.Authorization).toBe(
    "Bearer test-session-token",
  );
  expect(fetch.mock.calls[0][1].headers["Last-Event-ID"]).toBe("7");
  expect(result.headers.get("content-type")).toBe("text/event-stream");
  expect(await result.text()).not.toContain("test-session-token");
});
it("stores a successful login only in an httpOnly cookie", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ token: "test-login-token" })),
      ),
  );
  const result = await login(
    new NextRequest("https://admin.example/api/session", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        origin: "https://admin.example",
      },
      body: JSON.stringify({ password: "test-password" }),
    }),
  );
  expect(await result.json()).toEqual({ authenticated: true });
  const session = result.cookies.get("propadmin-session");
  expect(session).toMatchObject({
    value: "test-login-token",
    httpOnly: true,
    secure: true,
    sameSite: "lax",
  });
});
it("preserves authenticated statement downloads and their filenames", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response("%PDF-1.4", {
        headers: {
          "Content-Type": "application/pdf",
          "Content-Disposition": 'attachment; filename="landlord-2026-10.pdf"',
        },
      }),
    ),
  );
  const result = await GET(
    new NextRequest(
      "http://localhost:3000/api/backend/v1/statements/person%3Aowner?period=2026-10",
    ),
    {
      params: Promise.resolve({ path: ["v1", "statements", "person:owner"] }),
    },
  );
  expect(result.headers.get("content-type")).toBe("application/pdf");
  expect(result.headers.get("content-disposition")).toBe(
    'attachment; filename="landlord-2026-10.pdf"',
  );
  expect(await result.text()).toBe("%PDF-1.4");
});

it.each(["answer.md", "reasoning.md"])("preserves ticket Markdown download %s", async (filename) => {
  const markdown = "# Outcome\n\nRecorded cost: **£95**.\n";
  const fetch = vi.fn().mockResolvedValue(new Response(markdown, {
    headers: {
      "Content-Type": "text/markdown; charset=utf-8",
      "Content-Disposition": `attachment; filename="${filename}"`,
    },
  }));
  vi.stubGlobal("fetch", fetch);
  const result = await GET(new NextRequest(
    `http://localhost:3000/api/backend/v1/tickets/ticket%3Aquery/exports/${filename}`,
  ), { params: Promise.resolve({ path: ["v1", "tickets", "ticket:query", "exports", filename] }) });
  expect(fetch.mock.calls[0][1].headers.Authorization).toBe("Bearer test-session-token");
  expect(result.headers.get("content-type")).toBe("text/markdown; charset=utf-8");
  expect(result.headers.get("content-disposition")).toBe(`attachment; filename="${filename}"`);
  expect(await result.text()).toBe(markdown);
});
