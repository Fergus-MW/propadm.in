import { describe, expect, it } from "vitest";
import { groupTools } from "@/components/screens/admin-agent";

describe("groupTools", () => {
  it("collapses consecutive tool calls between messages", () => {
    const grouped = groupTools([
      { id: "1", type: "user.message", text: "hi" },
      { id: "2", tool: "list_admin_endpoints" },
      { id: "3", tool: "admin_api" },
      { id: "4", type: "agent.message", text: "done" },
      { id: "5", tool: "admin_api" },
    ]);
    expect(grouped.map((e) => e.tools ?? e.id)).toEqual([
      "1",
      ["list_admin_endpoints", "admin_api"],
      "4",
      ["admin_api"],
    ]);
  });
});
