import type { Entity, RecordData } from "./api";
export const nodeColors: Record<string, string> = {
  property: "--success",
  transaction: "--warning",
  service_provider: "--brand",
  service_offering: "--info",
  quote: "--danger",
};
export function graphQuery(
  type: string,
  entity: string | null,
  property: string,
  transactions: boolean,
): URLSearchParams {
  return new URLSearchParams({
    ...(type ? { type } : {}),
    ...(entity ? { entity_id: entity, depth: "2" } : {}),
    ...(property ? { property_id: property } : {}),
    include_transactions: String(Boolean(property && transactions)),
  });
}
export type GraphSnapshot = {
  nodes: Entity[];
  edges: RecordData[];
  version: number;
  positions: Float32Array;
  links: Float32Array;
};
/** The metadata length need not be aligned to 4 bytes; DataView keeps decoding safe. */
export function decodeGraph(buffer: ArrayBuffer): GraphSnapshot {
  if (buffer.byteLength < 16) throw new Error("Graph snapshot is truncated");
  const view = new DataView(buffer);
  if (new TextDecoder().decode(new Uint8Array(buffer, 0, 4)) !== "PGR1")
    throw new Error("Unsupported graph snapshot");
  const length = view.getUint32(4, true),
    nodesCount = view.getUint32(8, true),
    edgesCount = view.getUint32(12, true);
  const offset = 16 + length;
  if (offset + nodesCount * 8 + edgesCount * 8 !== buffer.byteLength)
    throw new Error("Graph snapshot has invalid lengths");
  const meta = JSON.parse(
    new TextDecoder().decode(new Uint8Array(buffer, 16, length)),
  );
  if (
    !Array.isArray(meta.nodes) ||
    !Array.isArray(meta.edges) ||
    meta.nodes.length !== nodesCount ||
    meta.edges.length !== edgesCount ||
    !Number.isSafeInteger(meta.version)
  )
    throw new Error("Graph metadata does not match snapshot");
  const positions = new Float32Array(nodesCount * 2),
    links = new Float32Array(edgesCount * 2);
  for (let i = 0; i < positions.length; i++) {
    positions[i] = view.getFloat32(offset + i * 4, true);
    if (!Number.isFinite(positions[i]))
      throw new Error("Graph contains invalid coordinates");
  }
  for (let i = 0; i < links.length; i++) {
    links[i] = view.getUint32(offset + positions.byteLength + i * 4, true);
    if (links[i] >= nodesCount)
      throw new Error("Graph link references a missing node");
  }
  return { ...meta, positions, links };
}
