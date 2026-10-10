import { afterEach, expect, it, vi } from "vitest";
import { api, apiClient, ApiError, endpoint } from "@/lib/api";
afterEach(() => vi.unstubAllGlobals());
it("generated client sends typed writes through the same authenticated proxy", async () => {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ id: "person:resident" }), { status: 201 }),
  );
  vi.stubGlobal("fetch", fetchMock);
  // Node's Request needs an absolute origin; browsers resolve the proxy base.
  await apiClient.POST("/v1/entities", { baseUrl: "http://localhost/api/backend", body: {
    type: "person", name: "Resident", description: "Local resident",
    reason: "Verify typed request", fields: { emails: ["resident@example.test"] },
  } });
  const request = fetchMock.mock.calls[0][0] as Request;
  expect(request.url).toBe("http://localhost/api/backend/v1/entities");
  expect(request.credentials).toBe("same-origin");
  expect(request.method).toBe("POST");
  expect(await request.json()).toMatchObject({ type: "person", name: "Resident" });
});
it("keeps data calls under authenticated same-origin gateway", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValue(
      new Response(JSON.stringify({ id: "ticket:a" }), { status: 201 }),
    );
  vi.stubGlobal("fetch", fetch);
  expect(endpoint("entities/ticket%3Aa")).toBe(
    "/api/backend/v1/entities/ticket%3Aa",
  );
  await api(
    "entities/ticket%3Aa",
    { version: 2, fields: { status: "done" } },
    "PATCH",
  );
  expect(fetch.mock.calls[0][1]).toMatchObject({
    credentials: "same-origin",
    method: "PATCH",
    body: '{"version":2,"fields":{"status":"done"}}',
  });
});
it("shows actual provider failures and conflicts as errors", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({ detail: "Rule compiler is not configured" }),
          { status: 503 },
        ),
      ),
  );
  await expect(
    api("edge-rules/compile", { prompt: "Find related companies" }),
  ).rejects.toMatchObject({
    message: "Rule compiler is not configured",
    status: 503,
  });
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ detail: "Version has changed" }), {
          status: 409,
        }),
      ),
  );
  await expect(
    api("entities/a", { version: 1 }, "PATCH"),
  ).rejects.toBeInstanceOf(ApiError);
});
