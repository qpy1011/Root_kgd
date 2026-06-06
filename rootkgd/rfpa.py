from __future__ import annotations

import heapq
import itertools
from dataclasses import dataclass

import numpy as np

from .graph import KnowledgeGraph


@dataclass(frozen=True)
class RfpaParameters:
    distances: dict[str, float]
    priorities: dict[str, int]
    sigma: float = 0.1
    max_starts: int = 5
    min_delta: float = 1e-8


def rfpa(
    graph: KnowledgeGraph,
    source: str,
    initial_fault: float,
    params: RfpaParameters,
) -> dict[str, float]:
    if source not in graph.nodes:
        raise KeyError(f"Unknown source node {source!r}")

    scores = {node: 0.0 for node in graph.nodes}
    receive_count = {node: 0 for node in graph.nodes}
    start_count = {node: 0 for node in graph.nodes}
    scores[source] = float(initial_fault)

    queue: list[tuple[int, int, str]] = []
    sequence = itertools.count()
    heapq.heappush(queue, (0, next(sequence), source))

    while queue:
        priority, _, head = heapq.heappop(queue)
        if start_count[head] >= params.max_starts:
            continue
        start_count[head] += 1

        for triple in graph.outgoing(head):
            distance = params.distances.get(triple.relation)
            relation_priority = params.priorities.get(triple.relation)
            if distance is None or relation_priority is None:
                continue

            sender_seen = receive_count[head] + 1
            path_loss = float(np.exp(-params.sigma * distance))
            receive_loss = 1.0 / sender_seen
            delta = scores[head] * path_loss * receive_loss
            if delta < params.min_delta:
                continue

            scores[triple.tail] += delta
            receive_count[triple.tail] += 1
            if start_count[triple.tail] < params.max_starts:
                heapq.heappush(
                    queue,
                    (priority + relation_priority, next(sequence), triple.tail),
                )

    return scores


def cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    left_norm = float(np.linalg.norm(left))
    right_norm = float(np.linalg.norm(right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return float(np.dot(left, right) / (left_norm * right_norm))


def root_scores(
    graph: KnowledgeGraph,
    contributions: dict[str, float],
    variable_nodes: list[str],
    params: RfpaParameters,
    candidates: list[str] | None = None,
    physical_initial_fault: float | None = None,
) -> list[tuple[str, float]]:
    if candidates is None:
        candidates = list(graph.nodes)
    target = np.array([contributions.get(node, 0.0) for node in variable_nodes], dtype=float)
    if physical_initial_fault is None:
        physical_initial_fault = max(contributions.values(), default=1.0)

    ranked: list[tuple[str, float]] = []
    for candidate in candidates:
        initial = contributions.get(candidate, physical_initial_fault)
        simulated = rfpa(graph, candidate, initial, params)
        vector = np.array([simulated.get(node, 0.0) for node in variable_nodes], dtype=float)
        ranked.append((candidate, cosine_similarity(vector, target)))
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked
