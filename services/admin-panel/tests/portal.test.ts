import { describe, expect, it } from "vitest";
import { needsYou, portalHref, type PortalItem } from "../lib/portal";
import { cleanUrl } from "../lib/analytics";
const item = (id: string, values: Partial<PortalItem> = {}) =>
  ({
    id,
    stage: 0,
    emergency: false,
    flags: [],
    autonomy: 3,
    draft: "",
    urgency: "Routine",
    due_at: null,
    ...values,
  }) as PortalItem;
describe("portal queue", () => {
  it("prioritises emergencies then deadline and excludes routine tags and closed work", () => {
    expect(
      needsYou([
        item("routine", { flags: ["boiler"] }),
        item("later", { autonomy: 2, due_at: "2026-10-10T14:00:00Z" }),
        item("earlier", { autonomy: 2, due_at: "2026-10-10T13:00:00Z" }),
        item("emergency", { flags: ["Emergency"], urgency: "Emergency" }),
        item("closed", { flags: ["Emergency"], stage: 11 }),
      ]).map((i) => i.id),
    ).toEqual(["emergency", "earlier", "later"]);
  });
  it("keeps dataset selection and safely encodes graph IDs in links", () => {
    expect(portalHref("inbox", true, "ticket:a/b")).toBe(
      "/portal/inbox/ticket%3Aa%2Fb?demo=1",
    );
  });
  it("does not expose magic link tokens in analytics URLs", () => {
    expect(cleanUrl("https://example.test/track/private-token?x=1")).toBe(
      "https://example.test/track/[redacted]",
    );
  });
});
