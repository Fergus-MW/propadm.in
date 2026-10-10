import posthog from "posthog-js";

let ready: Promise<boolean> | undefined;

export function cleanUrl(value: string): string {
  try {
    const url = new URL(value);
    return `${url.origin}${url.pathname.startsWith("/track/") ? "/track/[redacted]" : url.pathname}`;
  } catch {
    return "";
  }
}

export function initializeAnalytics(): Promise<boolean> {
  ready ??= (async () => {
    try {
      const response = await fetch("/api/analytics-config", {
        cache: "no-store",
      });
      if (!response.ok) return false;
      const config = await response.json();
      if (!config.projectToken?.startsWith("phc_")) return false;
      posthog.init(config.projectToken, {
        api_host: config.host,
        ui_host: "https://us.posthog.com",
        defaults: "2026-05-30",
        autocapture: false,
        capture_dead_clicks: false,
        capture_heatmaps: false,
        capture_performance: false,
        disable_surveys: true,
        capture_pageview: false,
        capture_pageleave: false,
        disable_session_recording: true,
        person_profiles: "never",
        advanced_disable_feature_flags: true,
        before_send: (event) => {
          if (!event) return event;
          if (
            typeof window !== "undefined" &&
            window.location.pathname.startsWith("/track/")
          )
            return null;
          if (
            !["$pageview", "admin_signed_in", "admin_signed_out"].includes(
              event.event,
            )
          )
            return null;
          event.properties.surface = "admin";
          event.properties.environment = config.environment;
          sanitizeProperties(event as unknown as Record<string, unknown>);
          return event;
        },
      });
      posthog.register({ surface: "admin", environment: config.environment });
      return true;
    } catch {
      return false;
    }
  })();
  return ready;
}

function sanitizeProperties(properties: Record<string, unknown>) {
  for (const [key, value] of Object.entries(properties)) {
    if (
      typeof value === "string" &&
      (key.endsWith("_url") || key.endsWith("referrer"))
    )
      properties[key] = cleanUrl(value);
    else if (value && typeof value === "object" && !Array.isArray(value))
      sanitizeProperties(value as Record<string, unknown>);
  }
}

export function captureAnalytics(
  event: string,
  properties: Record<string, unknown> = {},
) {
  void initializeAnalytics().then((enabled) => {
    if (enabled) posthog.capture(event, properties);
  });
}
