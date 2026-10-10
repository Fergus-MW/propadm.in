import { describe, expect, it } from "vitest";
import { decodeGraph } from "@/lib/graph";
function snapshot() {
  const nodes = [
    { id: "person:a", name: "A" },
    { id: "person:b", name: "B" },
  ];
  const edges = [{ id: "edge:a", source: "person:a", target: "person:b" }];
  const meta = new TextEncoder().encode(
    JSON.stringify({ nodes, edges, version: 7 }),
  );
  const buffer = new ArrayBuffer(16 + meta.length + 24),
    view = new DataView(buffer);
  new Uint8Array(buffer, 0, 4).set(new TextEncoder().encode("PGR1"));
  view.setUint32(4, meta.length, true);
  view.setUint32(8, 2, true);
  view.setUint32(12, 1, true);
  new Uint8Array(buffer, 16, meta.length).set(meta);
  [12.5, -20, 40, 80].forEach((n, i) =>
    view.setFloat32(16 + meta.length + i * 4, n, true),
  );
  view.setUint32(16 + meta.length + 16, 0, true);
  view.setUint32(16 + meta.length + 20, 1, true);
  return { buffer, offset: 16 + meta.length };
}
describe("binary graph protocol", () => {
  it("decodes metadata and unaligned typed data without losing layout", () => {
    const graph = decodeGraph(snapshot().buffer);
    expect(graph.version).toBe(7);
    expect(graph.nodes[0].id).toBe("person:a");
    expect([...graph.positions]).toEqual([12.5, -20, 40, 80]);
    expect([...graph.links]).toEqual([0, 1]);
  });
  it("rejects truncated and unknown snapshots", () => {
    expect(() => decodeGraph(new ArrayBuffer(8))).toThrow("truncated");
    const { buffer } = snapshot();
    new Uint8Array(buffer)[0] = 0;
    expect(() => decodeGraph(buffer)).toThrow("Unsupported");
    expect(() => decodeGraph(snapshot().buffer.slice(0, -4))).toThrow(
      "lengths",
    );
  });
  it("rejects invalid geometry and dangling node indexes", () => {
    const invalid = snapshot();
    new DataView(invalid.buffer).setFloat32(invalid.offset, NaN, true);
    expect(() => decodeGraph(invalid.buffer)).toThrow("coordinates");
    const dangling = snapshot();
    new DataView(dangling.buffer).setUint32(dangling.offset + 20, 99, true);
    expect(() => decodeGraph(dangling.buffer)).toThrow("missing node");
  });
});
