import { describe, expect, it } from "vitest";
import {
  editConflict,
  editableFields,
  expiry,
  minorUnits,
  money,
  queryPath,
  stalePrice,
} from "@/lib/property";
import { graphQuery } from "@/lib/graph";
import { bytesBase64, sourceMime } from "@/lib/source";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { Evidence } from "@/components/screens/entities";
import { decodeRouteSegment, sectionLabel } from "@/lib/routes";

describe("property ledger presentation", () => {
  it("decodes canonical route IDs once before constructing API requests", () => {
    expect(decodeRouteSegment("property%3Ahoxton-3b")).toBe(
      "property:hoxton-3b",
    );
    expect(decodeRouteSegment("person:existing")).toBe("person:existing");
    expect(decodeRouteSegment("property%3Aref%2525")).toBe("property:ref%25");
    expect(decodeRouteSegment("invalid%escape")).toBe("invalid%escape");
  });
  it("links prices to the exact source chunk for evidence inspection", () => {
    const html = renderToStaticMarkup(
      createElement(Evidence, {
        evidence: [
          {
            id: "chunk:price",
            document_id: "source_file:invoice",
            char_start: 30,
            char_end: 45,
            text: "boiler service",
          },
        ],
      }),
    );
    expect(html).toContain(
      "/documents/source_file%3Ainvoice?start=30&amp;end=45#source-highlight",
    );
    expect(html).toContain("boiler service");
  });
  it("preserves pence and rejects invalid or unsafe transaction amounts", () => {
    expect(minorUnits("950.01")).toBe(95001);
    expect(minorUnits("0.10")).toBe(10);
    expect(money(-10)).toBe("-£0.10");
    for (const input of [
      "0",
      "-4",
      "1.005",
      "NaN",
      "1e3",
      "9007199254740993",
    ]) {
      expect(() => minorUnits(input)).toThrow();
    }
  });
  it("keeps filters isolated and requires a selected property for transaction graph nodes", () => {
    expect(
      queryPath("ledger", {
        category: "rent_received",
        from: "",
        to: "2026-10-10",
      }),
    ).toBe("ledger?category=rent_received&to=2026-10-10");
    expect(graphQuery("", null, "", true).get("include_transactions")).toBe(
      "false",
    );
    const query = graphQuery("", null, "property:E1", true);
    expect(query.get("property_id")).toBe("property:E1");
    expect(query.get("include_transactions")).toBe("true");
    expect(
      editableFields(
        { ref: "P1", tenant_balance_minor: 5, rating: 4, observed: 2 },
        { observed: { read_only: true } },
      ),
    ).toEqual({ ref: "P1" });
  });
  it("preserves binary PDF uploads and financial source formats", () => {
    expect(sourceMime("notes.txt")).toBe("text/plain");
    expect(sourceMime("statement.CSV")).toBe("text/csv");
    expect(sourceMime("statement.ofx")).toBe("application/x-ofx");
    expect(sourceMime("invoice.pdf", "application/octet-stream")).toBe(
      "application/pdf",
    );
    const bytes = new Uint8Array([0, 37, 80, 68, 70, 255]);
    expect(
      Uint8Array.from(atob(bytesBase64(bytes)), (char) => char.charCodeAt(0)),
    ).toEqual(bytes);
  });
  it("flags expired accreditations and old or unknown prices", () => {
    const now = new Date("2026-10-10T00:00:00Z");
    expect(expiry("2026-10-09", now)).toBe("expired");
    expect(expiry("2026-11-01", now)).toBe("expiring");
    expect(expiry("2027-01-01", now)).toBe("valid");
    expect(expiry(undefined, now)).toBe("unknown");
    expect(stalePrice("2026-03-01", now)).toBe(true);
    expect(stalePrice(undefined, now)).toBe(true);
    expect(stalePrice("2026-10-01", now)).toBe(false);
  });
  it("keeps an open edit pinned to its starting version after a concurrent save", () => {
    expect(editConflict({ version: 3 }, { version: 3 })).toBeNull();
    expect(editConflict({ version: 3 }, { version: 4 })).toEqual({ from: 3, to: 4 });
  });
  it("labels breadcrumbs for routes outside the navigation", () => {
    const nav = [{ href: "/", label: "Today" }, { href: "/portal/inbox", label: "Inbox" }];
    expect(sectionLabel("/", nav)).toBe("Today");
    expect(sectionLabel("/portal/inbox", nav)).toBe("Inbox");
    expect(sectionLabel("/portal/settings", nav)).toBe("Settings");
  });
});
