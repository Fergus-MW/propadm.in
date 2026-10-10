"""Deterministic stored graph layout, so graph loads are instant and stable."""

import hashlib
import json
import math

from .store import publish

BOUND = 1000.0
GRAVITY = 1.0  # tuned with k so seeded graphs fill ~half the bounds


def compute_layout(state):
    """Fruchterman-Reingold seeded by stored positions; returns {id: (x, y)}.

    ponytail: O(n^2) repulsion per iteration (500 entities: ~6s cold, ~1s refine);
    switch to Barnes-Hut (quadtree) or let cosmos.gl own layout past ~1k entities.
    """
    nodes = sorted(
        key for key, entity in state["entities"].items() if not entity.get("merged_into")
    )
    if not nodes:
        return {}
    index = {key: i for i, key in enumerate(nodes)}
    links = {
        tuple(sorted((index[edge["source"]], index[edge["target"]])))
        for edge in state["edges"].values()
        if edge["source"] in index and edge["target"] in index and edge["source"] != edge["target"]
    }
    seen, pos, placed = set(), [], 0
    for i, key in enumerate(nodes):
        entity = state["entities"][key]
        point = (float(entity.get("layout_x") or 0), float(entity.get("layout_y") or 0))
        if point == (0.0, 0.0) or point in seen:
            # Unplaced or coincident: deterministic golden-angle spiral slot.
            radius = 40 * math.sqrt(i + 1)
            point = (math.cos(i * 2.399) * radius, math.sin(i * 2.399) * radius)
        else:
            placed += 1
        seen.add(point)
        pos.append(list(point))
    n = len(nodes)
    k = 0.6 * BOUND / math.sqrt(n)  # ideal link distance
    # Mostly-placed graphs only refine, so reruns barely move anything.
    settled = placed > n * 0.9
    temperature, iterations = (k * 0.05, 60) if settled else (k * 0.5, 300)
    for step in range(iterations):
        force = [[0.0, 0.0] for _ in range(n)]
        for a in range(n):
            ax, ay = pos[a]
            for b in range(a + 1, n):
                dx, dy = ax - pos[b][0], ay - pos[b][1]
                distance = math.hypot(dx, dy) or 0.01
                push = k * k / distance / distance
                force[a][0] += dx * push
                force[a][1] += dy * push
                force[b][0] -= dx * push
                force[b][1] -= dy * push
        for a, b in links:
            dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
            pull = math.hypot(dx, dy) / k
            force[a][0] -= dx * pull
            force[a][1] -= dy * pull
            force[b][0] += dx * pull
            force[b][1] += dy * pull
        limit = temperature * (1 - step / iterations)
        for i in range(n):
            # Gravity keeps disconnected satellites from drifting to the walls.
            fx, fy = force[i][0] - pos[i][0] * GRAVITY, force[i][1] - pos[i][1] * GRAVITY
            length = math.hypot(fx, fy)
            if length:
                scale = min(length, limit) / length
                pos[i][0] = max(-BOUND, min(BOUND, pos[i][0] + fx * scale))
                pos[i][1] = max(-BOUND, min(BOUND, pos[i][1] + fy * scale))
    return {key: (round(pos[i][0], 2), round(pos[i][1], 2)) for i, key in enumerate(nodes)}


def apply_layout(state):
    nodes = sorted(key for key, entity in state["entities"].items() if not entity.get("merged_into"))
    ids = set(nodes)
    links = sorted({tuple(sorted((edge["source"], edge["target"])))
                    for edge in state["edges"].values()
                    if edge["source"] in ids and edge["target"] in ids})
    signature = hashlib.sha256(json.dumps([nodes, links]).encode()).hexdigest()
    if state.get("layout_signature") == signature:
        publish(state, "layout.updated", {"count": 0})
        return {"moved": 0, "version": state["version"]}
    moved = 0
    for key, (x, y) in compute_layout(state).items():
        entity = state["entities"][key]
        if (entity.get("layout_x"), entity.get("layout_y")) != (x, y):
            # Position is presentation, not content: no entity version bump.
            entity.update(layout_x=x, layout_y=y)
            moved += 1
    state["layout_signature"] = signature
    publish(state, "layout.updated", {"count": moved})
    return {"moved": moved, "version": state["version"]}
