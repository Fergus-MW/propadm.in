import { decodeGraph } from "./graph";
self.onmessage = (event: MessageEvent<ArrayBuffer>) => {
  try {
    const graph = decodeGraph(event.data);
    self.postMessage(
      { graph },
      { transfer: [graph.positions.buffer, graph.links.buffer] },
    );
  } catch (error) {
    self.postMessage({
      error: error instanceof Error ? error.message : "Invalid graph",
    });
  }
};
