"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import type { Graph } from "@cosmos.gl/graph";
import { Expand, RefreshCw } from "lucide-react";
import { Header, State, Status } from "../common";
import { FormInput, FormSelect } from "../ui/Input";
import { Button } from "../ui/Button";
import { endpoint, str } from "@/lib/api";
import { useItems } from "@/lib/hooks";
import { graphQuery, nodeColors, type GraphSnapshot } from "@/lib/graph";
import type { Entity } from "@/lib/api";
import { entityHref } from "@/lib/property";
function canvasColor(token: string): string {
  const probe = document.createElement("span");
  probe.style.color = `var(${token})`;
  document.body.append(probe);
  const color = getComputedStyle(probe).color;
  probe.remove();
  return color;
}
function pointColors(nodes: Entity[]): Float32Array {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 1;
  const context = canvas.getContext("2d");
  const colors = new Float32Array(nodes.length * 4);
  if (!context) return colors;
  nodes.forEach((node, i) => {
    context.clearRect(0, 0, 1, 1);
    context.fillStyle = canvasColor(nodeColors[node.type] ?? "--foreground");
    context.fillRect(0, 0, 1, 1);
    const rgba = context.getImageData(0, 0, 1, 1).data;
    colors.set(
      Array.from(rgba, (value) => value / 255),
      i * 4,
    );
  });
  return colors;
}
export function GraphExplorer() {
  const container = useRef<HTMLDivElement>(null);
  const graphRef = useRef<Graph | null>(null);
  const snapshotRef = useRef<GraphSnapshot | null>(null);
  const [snapshot, setSnapshot] = useState<GraphSnapshot | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [pending, setPending] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [type, setType] = useState("");
  const [connected, setConnected] = useState(false);
  const [reload, setReload] = useState(0);
  const params = useSearchParams();
  const entity = params.get("entity");
  const types = useItems("entity-types");
  const properties = useItems("properties");
  const [property, setProperty] = useState(params.get("property") ?? "");
  const [transactions, setTransactions] = useState(
    params.get("transactions") === "true",
  );
  useEffect(() => {
    let disposed = false;
    let stream: EventSource | undefined;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let activeRequest = false;
    let queued = false;
    const abort = new AbortController();
    const worker = new Worker(
      new URL("../../lib/graph.worker.ts", import.meta.url),
    );
    worker.onmessage = async ({
      data,
    }: MessageEvent<{ graph?: GraphSnapshot; error?: string }>) => {
      if (disposed) return;
      activeRequest = false;
      if (data.error) {
        setError(new Error(data.error));
        setPending(false);
        return;
      }
      if (!data.graph) return;
      const snapshot = data.graph;
      snapshotRef.current = snapshot;
      setSnapshot(snapshot);
      setPending(false);
      try {
        if (!graphRef.current && container.current) {
          const { Graph } = await import("@cosmos.gl/graph");
          if (disposed) return;
          graphRef.current = new Graph(container.current, {
            enableSimulation: false,
            rescalePositions: true,
            fitViewOnInit: true,
            fitViewDelay: 100,
            fitViewPadding: 0.18,
            backgroundColor: canvasColor("--viz-canvas"),
            pointColor: canvasColor("--brand"),
            pointSize: 6,
            linkColor: canvasColor("--palette-line"),
            linkWidth: 1,
            onClick: (index) => {
              if (index !== undefined)
                setSelected(snapshotRef.current?.nodes[index]?.id ?? null);
            },
          });
        }
        const graph = graphRef.current;
        if (graph) {
          graph.setPointPositions(snapshot.positions);
          graph.setLinks(snapshot.links);
          graph.setPointColors(pointColors(snapshot.nodes));
          graph.render();
          if (entity) {
            const i = snapshot.nodes.findIndex((n) => n.id === entity);
            if (i >= 0) {
              graph.selectPointByIndex(i, true);
              graph.fitViewByPointIndices([i], 300, 0.5);
              setSelected(entity);
            }
          }
        }
        setError(null);
      } catch (reason) {
        setError(
          reason instanceof Error
            ? reason
            : new Error("WebGL unavailable. Use the accessible entity list."),
        );
      }
      if (queued) {
        queued = false;
        void load();
      }
    };
    async function load() {
      if (activeRequest) {
        queued = true;
        return;
      }
      activeRequest = true;
      try {
        const query = graphQuery(type, entity, property, transactions);
        const response = await fetch(endpoint(`entities/graph.bin?${query}`), {
          signal: abort.signal,
        });
        if (!response.ok)
          throw new Error(`Cannot load graph (${response.status})`);
        const buffer = await response.arrayBuffer();
        if (!disposed) worker.postMessage(buffer, [buffer]);
      } catch (reason) {
        activeRequest = false;
        if (!disposed) {
          setError(
            reason instanceof Error ? reason : new Error("Cannot load graph"),
          );
          setPending(false);
        }
      }
    }
    const theme = () => {
      graphRef.current?.setConfig({
        backgroundColor: canvasColor("--viz-canvas"),
        pointColor: canvasColor("--brand"),
        linkColor: canvasColor("--palette-line"),
      });
      if (snapshotRef.current)
        graphRef.current?.setPointColors(
          pointColors(snapshotRef.current.nodes),
        );
      graphRef.current?.render();
    };
    window.addEventListener("propadmin-theme", theme);
    void load().then(() => {
      if (disposed) return;
      stream = new EventSource(endpoint("entities/graph/stream"));
      stream.onopen = () => setConnected(true);
      stream.onerror = () => setConnected(false);
      const change = () => {
        if (!timer)
          timer = setTimeout(() => {
            timer = undefined;
            void load();
          }, 250);
      };
      stream.addEventListener("delta", change);
      stream.addEventListener("reset", change);
    });
    return () => {
      disposed = true;
      abort.abort();
      worker.terminate();
      stream?.close();
      clearTimeout(timer);
      window.removeEventListener("propadmin-theme", theme);
      graphRef.current?.destroy();
      graphRef.current = null;
    };
  }, [type, entity, property, transactions, reload]);
  const current = snapshot?.nodes.find((n) => n.id === selected);
  const visible = (snapshot?.nodes ?? []).filter((n) =>
    `${n.name} ${n.id}`.toLowerCase().includes(q.toLowerCase()),
  );
  return (
    <>
      <Header title="Graph explorer">
        <Status value={connected ? "live" : "reconnecting"} />
        <Button variant="ghost" onClick={() => setReload((n) => n + 1)}>
          <RefreshCw size={14} />
          Reload
        </Button>
      </Header>
      <div className="filter-row">
        <FormInput
          label="Find a node"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Name or identifier"
        />
        <FormSelect
          label="Entity type"
          value={type}
          onChange={(e) => setType(e.target.value)}
          options={[
            { value: "", label: "All types" },
            ...(types.data?.items ?? []).map((t) => ({
              value: t.id,
              label: str(t.name),
            })),
          ]}
        />
      </div>
      <div className="filter-row">
        <FormSelect
          label="Property ledger"
          value={property}
          onChange={(e) => setProperty(e.target.value)}
          options={[
            { value: "", label: "Select property" },
            ...(properties.data?.items ?? []).map((row) => ({
              value: row.id,
              label: str(row.name),
            })),
          ]}
        />
        <label className="actions">
          <input
            type="checkbox"
            disabled={!property}
            checked={Boolean(property && transactions)}
            onChange={(e) => setTransactions(e.target.checked)}
          />
          Show transactions for this property
        </label>
      </div>
      <div className="actions caption mb-6" aria-label="Node type colours">
        {Object.entries(nodeColors).map(([type, token]) => (
          <span key={type}>
            <span style={{ color: `var(${token})` }} aria-hidden="true">
              ■{" "}
            </span>
            {type.replaceAll("_", " ")}
          </span>
        ))}
      </div>
      <State
        pending={pending}
        error={error}
        retry={() => setReload((n) => n + 1)}
      />
      <div className="graph-layout">
        <div className="graph-stage">
          <div
            ref={container}
            className="graph-canvas"
            aria-label="Interactive entity relationship graph"
          />
          <div className="graph-controls">
            <Button
              variant="ghost"
              onClick={() => graphRef.current?.fitView(300, 0.18)}
            >
              <Expand size={14} />
              Fit graph
            </Button>
            <span className="caption">
              {snapshot?.nodes.length ?? 0} nodes ·{" "}
              {snapshot?.edges.length ?? 0} connections
            </span>
          </div>
          <div className="graph-labels">
            <span>Drag to pan</span>
            <span>Scroll to zoom</span>
            <span>Select to inspect</span>
          </div>
        </div>
        <aside>
          <div className="node-list">
            {visible.slice(0, 200).map((node) => (
              <button
                key={node.id}
                className="node-item draw-underline"
                onClick={() => {
                  const index =
                    snapshot?.nodes.findIndex((n) => n.id === node.id) ?? -1;
                  if (index >= 0)
                    graphRef.current?.selectPointByIndex(index, true);
                  setSelected(node.id);
                }}
              >
                <strong>{node.name}</strong>
                <small>{node.type}</small>
              </button>
            ))}
            {visible.length > 200 && (
              <p className="caption py-4">
                Showing 200 matches. Refine the search to find another node.
              </p>
            )}
          </div>
          {current && (
            <div className="result">
              <h3>{current.name}</h3>
              <p>{current.description}</p>
              <Link className="draw-underline" href={entityHref(current)}>
                Open entity ↗
              </Link>
            </div>
          )}
        </aside>
      </div>
    </>
  );
}
