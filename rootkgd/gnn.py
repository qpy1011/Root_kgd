from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Iterable

import numpy as np

from .graph import KnowledgeGraph
from .rfpa import cosine_similarity


EPSILON = 1e-12


@dataclass(frozen=True)
class GnnParameters:
    relation_weights: dict[str, float]
    edge_weights: dict[str, float] | None = None
    self_weight: float = 0.0
    layers: int = 3


@dataclass(frozen=True)
class GnnTrainingCase:
    name: str
    contributions: dict[str, float]
    positive_nodes: tuple[str, ...]


@dataclass(frozen=True)
class GnnTrainingResult:
    params: GnnParameters
    base_loss: float
    final_loss: float
    history: list[float]


def edge_key(head: str, relation: str, tail: str) -> str:
    return f"{head}|{relation}|{tail}"


def gnn_propagate(
    graph: KnowledgeGraph,
    source: str,
    initial_fault: float,
    params: GnnParameters,
) -> dict[str, float]:
    if source not in graph.nodes:
        raise KeyError(f"Unknown source node {source!r}")
    if params.layers < 0:
        raise ValueError("layers must be non-negative")

    scores = {}
    frontier = {}
    scores[source] = float(initial_fault)
    frontier[source] = float(initial_fault)

    for _ in range(params.layers):
        next_frontier: dict[str, float] = {}
        if params.self_weight:
            for node, value in frontier.items():
                if value:
                    next_frontier[node] = next_frontier.get(node, 0.0) + value * params.self_weight

        for head, value in frontier.items():
            if not value:
                continue
            for triple in graph.outgoing(head):
                weight = edge_weight(params, triple.head, triple.relation, triple.tail)
                if weight is None:
                    continue
                next_frontier[triple.tail] = next_frontier.get(triple.tail, 0.0) + value * max(0.0, weight)

        if all(abs(value) <= EPSILON for value in next_frontier.values()):
            break

        for node, value in next_frontier.items():
            scores[node] = scores.get(node, 0.0) + value
        frontier = next_frontier

    return scores


def gnn_root_scores(
    graph: KnowledgeGraph,
    contributions: dict[str, float],
    variable_nodes: list[str],
    params: GnnParameters,
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
        simulated = gnn_propagate(graph, candidate, initial, params)
        vector = np.array([simulated.get(node, 0.0) for node in variable_nodes], dtype=float)
        ranked.append((candidate, cosine_similarity(vector, target)))
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked


def gnn_ranking_loss(
    graph: KnowledgeGraph,
    cases: Iterable[GnnTrainingCase],
    variable_nodes: list[str],
    params: GnnParameters,
    margin: float = 0.05,
    candidates: list[str] | None = None,
) -> float:
    losses: list[float] = []
    candidate_nodes = candidates or list(graph.nodes)
    for case in cases:
        case_candidates = list(dict.fromkeys([*candidate_nodes, *case.positive_nodes]))
        ranked = dict(gnn_root_scores(graph, case.contributions, variable_nodes, params, case_candidates))
        positive_scores = [ranked[node] for node in case.positive_nodes if node in ranked]
        if not positive_scores:
            continue
        negative_scores = [
            score for node, score in ranked.items() if node not in set(case.positive_nodes)
        ]
        if not negative_scores:
            losses.extend(1.0 - score for score in positive_scores)
            continue
        hardest_negative = max(negative_scores)
        losses.extend(max(0.0, margin + hardest_negative - score) for score in positive_scores)
    if not losses:
        return 0.0
    return float(np.mean(losses))


def fit_gnn_parameters(
    graph: KnowledgeGraph,
    cases: Iterable[GnnTrainingCase],
    variable_nodes: list[str],
    base_params: GnnParameters,
    epochs: int = 4,
    regularization: float = 0.01,
    max_trainable_edges: int = 80,
    hard_negatives_per_case: int = 8,
) -> GnnTrainingResult:
    case_list = list(cases)
    train_candidates = sorted(
        training_candidate_nodes(
            graph,
            case_list,
            variable_nodes,
            base_params,
            hard_negatives_per_case=hard_negatives_per_case,
        )
    )
    base_loss = gnn_ranking_loss(graph, case_list, variable_nodes, base_params, candidates=train_candidates)
    best_params = base_params
    best_loss = _regularized_loss(
        graph,
        case_list,
        variable_nodes,
        base_params,
        base_params,
        regularization,
        candidates=train_candidates,
    )
    history = [best_loss]
    edge_keys = sorted(
        trainable_edge_keys(
            graph,
            case_list,
            variable_nodes,
            max_edges=max_trainable_edges,
        )
        if base_params.edge_weights
        else {}
    )
    relations = sorted(base_params.relation_weights)

    for epoch in range(epochs):
        step = 0.5 ** epoch
        search_keys = edge_keys if edge_keys else relations
        for key in search_keys:
            current = (
                (best_params.edge_weights or {})[key]
                if edge_keys
                else best_params.relation_weights[key]
            )
            candidates = [current, current * (1.0 - step), current * (1.0 + step), step]
            for candidate in candidates:
                trial_params = _replace_weight(best_params, key, _clip_weight(candidate), use_edge_weights=bool(edge_keys))
                trial_loss = _regularized_loss(
                    graph,
                    case_list,
                    variable_nodes,
                    trial_params,
                    base_params,
                    regularization,
                    candidates=train_candidates,
                )
                if trial_loss + EPSILON < best_loss:
                    best_loss = trial_loss
                    best_params = trial_params
        history.append(best_loss)

    final_loss = gnn_ranking_loss(graph, case_list, variable_nodes, best_params, candidates=train_candidates)
    return GnnTrainingResult(
        params=best_params,
        base_loss=base_loss,
        final_loss=final_loss,
        history=history,
    )


def initial_gnn_parameters_from_rfpa(
    relations: Iterable[str],
    distances: dict[str, float],
    sigma: float,
    layers: int = 4,
    graph: KnowledgeGraph | None = None,
) -> GnnParameters:
    weights = {
        relation: float(np.exp(-sigma * distances.get(relation, 1.0)))
        for relation in sorted(set(relations))
    }
    edge_weights = None
    if graph is not None:
        edge_weights = {
            edge_key(triple.head, triple.relation, triple.tail): weights.get(triple.relation, 0.0)
            for triple in graph.triples
        }
    return GnnParameters(relation_weights=weights, edge_weights=edge_weights, self_weight=0.0, layers=layers)


def with_edge_weights_from_graph(graph: KnowledgeGraph, params: GnnParameters) -> GnnParameters:
    return GnnParameters(
        relation_weights=dict(params.relation_weights),
        edge_weights={
            edge_key(triple.head, triple.relation, triple.tail): edge_weight(
                params,
                triple.head,
                triple.relation,
                triple.tail,
            )
            or 0.0
            for triple in graph.triples
        },
        self_weight=params.self_weight,
        layers=params.layers,
    )


def make_training_cases_from_targets(
    case_results: Iterable[object],
    targets: dict[int, object],
) -> list[GnnTrainingCase]:
    cases: list[GnnTrainingCase] = []
    for result in case_results:
        target = targets.get(result.fault_id)
        if target is None:
            continue
        positive_nodes = tuple(target.root_variables + target.physical_roots)
        cases.append(
            GnnTrainingCase(
                name=f"IDV({result.fault_id})",
                contributions=dict(result.contributions),
                positive_nodes=positive_nodes,
            )
        )
    return cases


def trainable_edge_keys(
    graph: KnowledgeGraph,
    cases: Iterable[GnnTrainingCase],
    variable_nodes: list[str],
    *,
    hops: int = 2,
    top_contribution_nodes: int = 8,
    max_edges: int | None = None,
) -> set[str]:
    seeds: set[str] = set()
    variable_set = set(variable_nodes)
    for case in cases:
        seeds.update(node for node in case.positive_nodes if node in graph.nodes)
        top_nodes = sorted(
            (
                (node, float(score))
                for node, score in case.contributions.items()
                if node in variable_set and node in graph.nodes
            ),
            key=lambda item: item[1],
            reverse=True,
        )[:top_contribution_nodes]
        seeds.update(node for node, _ in top_nodes)

    selected: set[str] = set()
    frontier = set(seeds)
    visited = set(seeds)
    for _ in range(max(0, hops)):
        next_frontier: set[str] = set()
        for head in sorted(frontier):
            for triple in graph.outgoing(head):
                selected.add(edge_key(triple.head, triple.relation, triple.tail))
                if triple.tail not in visited:
                    next_frontier.add(triple.tail)
                    visited.add(triple.tail)
        frontier = next_frontier
        if not frontier:
            break

    if max_edges is not None and len(selected) > max_edges:
        ranked_edges = sorted(
            selected,
            key=lambda key: _edge_priority(key, seeds, graph),
        )
        return set(ranked_edges[:max_edges])
    return selected


def training_candidate_nodes(
    graph: KnowledgeGraph,
    cases: Iterable[GnnTrainingCase],
    variable_nodes: list[str],
    params: GnnParameters,
    *,
    top_contribution_nodes: int = 10,
    hard_negatives_per_case: int = 8,
) -> set[str]:
    candidates: set[str] = set()
    variable_set = set(variable_nodes)
    for case in cases:
        positives = {node for node in case.positive_nodes if node in graph.nodes}
        candidates.update(positives)
        top_nodes = sorted(
            (
                (node, float(score))
                for node, score in case.contributions.items()
                if node in variable_set and node in graph.nodes
            ),
            key=lambda item: item[1],
            reverse=True,
        )[:top_contribution_nodes]
        candidates.update(node for node, _ in top_nodes)
        ranked = gnn_root_scores(graph, case.contributions, variable_nodes, params)
        hard_negatives = [
            node
            for node, _ in ranked
            if node not in positives
        ][:hard_negatives_per_case]
        candidates.update(hard_negatives)
    return candidates


def leave_one_out_splits(items: list[GnnTrainingCase]) -> Iterable[tuple[list[GnnTrainingCase], GnnTrainingCase]]:
    for index, item in enumerate(items):
        train = [candidate for i, candidate in enumerate(items) if i != index]
        yield train, item


def grid_search_parameters(
    graph: KnowledgeGraph,
    cases: Iterable[GnnTrainingCase],
    variable_nodes: list[str],
    relations: Iterable[str],
    candidate_weights: Iterable[float],
    layers: int,
) -> GnnTrainingResult:
    relation_list = sorted(set(relations))
    case_list = list(cases)
    weight_values = list(candidate_weights)
    if not relation_list:
        raise ValueError("At least one relation is required")
    if not weight_values:
        raise ValueError("At least one candidate weight is required")

    base_weight = float(np.mean(weight_values))
    base_params = GnnParameters(
        relation_weights={relation: base_weight for relation in relation_list},
        layers=layers,
    )
    best_params = base_params
    base_loss = gnn_ranking_loss(graph, case_list, variable_nodes, base_params)
    best_loss = base_loss

    for values in product(weight_values, repeat=len(relation_list)):
        params = GnnParameters(
            relation_weights=dict(zip(relation_list, map(float, values), strict=True)),
            layers=layers,
        )
        loss = gnn_ranking_loss(graph, case_list, variable_nodes, params)
        if loss + EPSILON < best_loss:
            best_loss = loss
            best_params = params

    return GnnTrainingResult(
        params=best_params,
        base_loss=base_loss,
        final_loss=best_loss,
        history=[base_loss, best_loss],
    )


def _regularized_loss(
    graph: KnowledgeGraph,
    cases: list[GnnTrainingCase],
    variable_nodes: list[str],
    params: GnnParameters,
    base_params: GnnParameters,
    regularization: float,
    candidates: list[str] | None = None,
) -> float:
    loss = gnn_ranking_loss(graph, cases, variable_nodes, params, candidates=candidates)
    if regularization <= 0.0:
        return loss
    penalty = 0.0
    if params.edge_weights:
        base_edge_weights = base_params.edge_weights or {}
        for key, weight in params.edge_weights.items():
            base = base_edge_weights.get(key, relation_prior_for_edge_key(key, base_params.relation_weights))
            relation_prior = relation_prior_for_edge_key(key, base_params.relation_weights)
            penalty += (weight - base) ** 2
            penalty += 0.25 * (weight - relation_prior) ** 2
    else:
        for relation, weight in params.relation_weights.items():
            base = base_params.relation_weights.get(relation, 0.0)
            penalty += (weight - base) ** 2
    return loss + regularization * penalty


def edge_weight(params: GnnParameters, head: str, relation: str, tail: str) -> float | None:
    if params.edge_weights is not None:
        key = edge_key(head, relation, tail)
        if key in params.edge_weights:
            return params.edge_weights[key]
    return params.relation_weights.get(relation)


def relation_prior_for_edge_key(key: str, relation_weights: dict[str, float]) -> float:
    parts = key.split("|", 2)
    if len(parts) != 3:
        return 0.0
    return relation_weights.get(parts[1], 0.0)


def _replace_weight(params: GnnParameters, key: str, value: float, *, use_edge_weights: bool) -> GnnParameters:
    if use_edge_weights:
        edge_weights = dict(params.edge_weights or {})
        edge_weights[key] = value
        return GnnParameters(
            relation_weights=dict(params.relation_weights),
            edge_weights=edge_weights,
            self_weight=params.self_weight,
            layers=params.layers,
        )
    relation_weights = dict(params.relation_weights)
    relation_weights[key] = value
    return GnnParameters(
        relation_weights=relation_weights,
        edge_weights=params.edge_weights,
        self_weight=params.self_weight,
        layers=params.layers,
    )


def _edge_priority(key: str, seeds: set[str], graph: KnowledgeGraph) -> tuple[int, int, str]:
    head, relation, tail = key.split("|", 2)
    touches_seed = 0 if head in seeds or tail in seeds else 1
    relation_rank = {"State": 0, "State of": 1, "Output": 2, "Contain": 3, "Contained by": 4, "Generate": 5}.get(relation, 9)
    degree_rank = len(graph.outgoing(head))
    return (touches_seed, relation_rank, degree_rank, key)


def _clip_weight(value: float) -> float:
    return float(np.clip(value, 0.0, 2.0))
