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

    scores = {node: 0.0 for node in graph.nodes}
    frontier = {node: 0.0 for node in graph.nodes}
    scores[source] = float(initial_fault)
    frontier[source] = float(initial_fault)

    for _ in range(params.layers):
        next_frontier = {node: 0.0 for node in graph.nodes}
        if params.self_weight:
            for node, value in frontier.items():
                if value:
                    next_frontier[node] += value * params.self_weight

        for head, value in frontier.items():
            if not value:
                continue
            for triple in graph.outgoing(head):
                weight = params.relation_weights.get(triple.relation)
                if weight is None:
                    continue
                next_frontier[triple.tail] += value * max(0.0, weight)

        if all(abs(value) <= EPSILON for value in next_frontier.values()):
            break

        for node, value in next_frontier.items():
            scores[node] += value
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
) -> float:
    losses: list[float] = []
    candidates = list(graph.nodes)
    for case in cases:
        ranked = dict(gnn_root_scores(graph, case.contributions, variable_nodes, params, candidates))
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
) -> GnnTrainingResult:
    case_list = list(cases)
    base_loss = gnn_ranking_loss(graph, case_list, variable_nodes, base_params)
    best_params = base_params
    best_loss = _regularized_loss(graph, case_list, variable_nodes, base_params, base_params, regularization)
    history = [best_loss]
    relations = sorted(base_params.relation_weights)

    for epoch in range(epochs):
        step = 0.5 ** epoch
        for relation in relations:
            current = best_params.relation_weights[relation]
            candidates = [current, current * (1.0 - step), current * (1.0 + step), step]
            for candidate in candidates:
                trial_weights = dict(best_params.relation_weights)
                trial_weights[relation] = _clip_weight(candidate)
                trial_params = GnnParameters(
                    relation_weights=trial_weights,
                    self_weight=best_params.self_weight,
                    layers=best_params.layers,
                )
                trial_loss = _regularized_loss(
                    graph,
                    case_list,
                    variable_nodes,
                    trial_params,
                    base_params,
                    regularization,
                )
                if trial_loss + EPSILON < best_loss:
                    best_loss = trial_loss
                    best_params = trial_params
        history.append(best_loss)

    final_loss = gnn_ranking_loss(graph, case_list, variable_nodes, best_params)
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
) -> GnnParameters:
    weights = {
        relation: float(np.exp(-sigma * distances.get(relation, 1.0)))
        for relation in sorted(set(relations))
    }
    return GnnParameters(relation_weights=weights, self_weight=0.0, layers=layers)


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
) -> float:
    loss = gnn_ranking_loss(graph, cases, variable_nodes, params)
    if regularization <= 0.0:
        return loss
    penalty = 0.0
    for relation, weight in params.relation_weights.items():
        base = base_params.relation_weights.get(relation, 0.0)
        penalty += (weight - base) ** 2
    return loss + regularization * penalty


def _clip_weight(value: float) -> float:
    return float(np.clip(value, 0.0, 2.0))
