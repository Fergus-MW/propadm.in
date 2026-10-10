import { beforeEach, expect, it, vi } from "vitest";
import { GET } from "@/app/api/analytics-config/route";

const sdk = vi.hoisted(() => ({ init: vi.fn(), capture: vi.fn(), register: vi.fn() }));
vi.mock("posthog-js", () => ({ default: sdk }));

beforeEach(() => {
  vi.resetModules();
  vi.clearAllMocks();
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

it("reads public config at runtime and never exposes a personal API key", async () => {
  vi.stubEnv("POSTHOG_PROJECT_TOKEN", "phc_test");
  expect((await GET().json()).projectToken).toBe("phc_test");
  vi.stubEnv("POSTHOG_PROJECT_TOKEN", "phx_private");
  expect((await GET().json()).projectToken).toBe("");
  expect(GET().headers.get("cache-control")).toBe("no-store");
});

it("initializes once, waits for config, and removes private URL parameters", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({
    projectToken: "phc_test", host: "https://us.i.posthog.com", environment: "test",
  })));
  const { initializeAnalytics, captureAnalytics } = await import("@/lib/analytics");
  captureAnalytics("admin_signed_in");
  await initializeAnalytics();
  await initializeAnalytics();
  expect(sdk.init).toHaveBeenCalledTimes(1);
  expect(sdk.capture).toHaveBeenCalledWith("admin_signed_in", {});
  const config = sdk.init.mock.calls[0][1];
  expect(config.autocapture).toBe(false);
  expect(config.disable_session_recording).toBe(true);
  const event = { event: "$pageview", properties: {
    $current_url: "https://app.example/search?q=tenant#private",
    $set_once: { $initial_current_url: "https://app.example/?email=private" },
  }, $set_once: { $initial_current_url: "https://app.example/?email=private" } };
  expect(config.before_send(event).properties.$current_url).toBe("https://app.example/search");
  expect(event.properties.$set_once.$initial_current_url).toBe("https://app.example/");
  expect(event.$set_once.$initial_current_url).toBe("https://app.example/");
  expect(config.before_send({ event: "$autocapture", properties: {} })).toBeNull();
});

it("does not interrupt the app if analytics config is unavailable", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
  const { initializeAnalytics } = await import("@/lib/analytics");
  expect(await initializeAnalytics()).toBe(false);
  expect(sdk.init).not.toHaveBeenCalled();
});
