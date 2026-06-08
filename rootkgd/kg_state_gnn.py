from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .gnn import edge_key, relation_prior_for_edge_key
from .graph import KnowledgeGraph
from .rfpa import cosine_similarity


EPSILON = 1e-12
STATE_NAMES = ("high", "low", "rise", "fall")
STATE_RELATION = "Has abnormal state"
STATE_BACK_RELATION = "State evidence of"


@dataclass(frozen=True)
class StateKgGnnParameters:
    relation_weights: dict[str, float]
    edge_weights: dict[str, float] | None = None
    self_weight: float = 0.0
    layers: int = 4
    state_gate_strength: float = 0.75
    state_target_weight: float = 0.35


@dataclass(frozen=True)
class StateKgGnnCase:
    name: str
    contributions: dict[str, float]
    state_evidence: dict[str, float]
    positive_nodes: tuple[str, ...]


@dataclass(frozen=True)
class StateKgGnnTrainingResult:
    params: StateKgGnnParameters
    base_loss: float
    final_loss: float
    history: list[float]


def state_node_name(variable: str, state: str) -> str:
    if state not in STATE_NAMES:
        raise ValueError(f"Unknown abnormal state {state!r}")
    return f"{variable}::{state}"


def is_state_node(node: str) -> bool:
    return node.rsplit("::", 1)[-1] in STATE_NAMES and "::" in node


def state_target_nodes(variable_nodes: Iterable[str]) -> list[str]:
    return [
        state_node_name(variable, state)
        for variable in variable_nodes
        for state in STATE_NAMES
    ]


def augment_graph_with_state_nodes(graph: KnowledgeGraph, variable_nodes: Iterable[str]) -> KnowledgeGraph:
    augmented = KnowledgeGraph()
    for name, node in graph.nodes.items():
        augmented.add_node(name, node.kind)
    for triple in graph.triples:
        _add_edge_once(augmented, triple.head, triple.relation, triple.tail)

    for variable in variable_nodes:
        augmented.add_node(variable, graph.nodes.get(variable, augmented.nodes.get(variable)).kind)
        for state in STATE_NAMES:
            node = state_node_name(variable, state)
            augmented.add_node(node, "state")
            _add_edge_once(augmented, variable, STATE_RELATION, node)
            _add_edge_once(augmented, node, STATE_BACK_RELATION, variable)
    return augmented


def compute_state_evidence(
    normal_data: np.ndarray,
    fault_samples: np.ndarray,
    variable_nodes: list[str],
) -> dict[str, float]:
    if normal_data.ndim != 2 or fault_samples.ndim != 2:
        raise ValueError("normal_data and fault_samples must be two-dimensional")
    width = len(variable_nodes)
    if normal_data.shape[1] < width or fault_samples.shape[1] < width:
        raise ValueError("data arrays do not contain enough columns for variable_nodes")

    normal = normal_data[:, :width].astype(float)
    samples = fault_samples[:, :width].astype(float)
    mean = normal.mean(axis=0)
    std = _safe_scale(normal.std(axis=0))
    normal_z = (normal - mean) / std
    sample_z = (samples - mean) / std

    level = sample_z.mean(axis=0)
    if sample_z.shape[0] > 1 and normal_z.shape[0] > 1:
        normal_delta = np.diff(normal_z, axis=0)
        sample_delta = np.diff(sample_z, axis=0)
        delta_scale = _safe_scale(normal_delta.std(axis=0))
        trend = sample_delta.mean(axis=0) / delta_scale
    else:
        trend = np.zeros(width, dtype=float)

    high = _positive_evidence(level)
    low = _positive_evidence(-level)
    rise = _positive_evidence(trend)
    fall = _positive_evidence(-trend)

    evidence: dict[str, float] = {}
    for index, variable in enumerate(variable_nodes):
        evidence[state_node_name(variable, "high")] = float(high[index])
        evidence[state_node_name(variable, "low")] = float(low[index])
        evidence[state_node_name(variable, "rise")] = float(rise[index])
        evidence[state_node_name(variable, "fall")] = float(fall[index])
    return evidence


def initial_state_kg_gnn_parameters(
    graph: KnowledgeGraph,
    relation_weights: dict[str, float],
    *,
    layers: int = 4,
    self_weight: float = 0.0,
    state_gate_strength: float = 0.75,
    state_target_weight: float = 0.35,
) -> StateKgGnnParameters:
    completed_relation_weights = dict(relation_weights)
    for triple in graph.triples:
        completed_relation_weights.setdefault(triple.relation, 0.5)
    return StateKgGnnParameters(
        relation_weights=completed_relation_weights,
        edge_weights={
            edge_key(triple.head, triple.relation, triple.tail): completed_relation_weights[triple.relation]
            for triple in graph.triples
        },
        self_weight=self_weight,
        layers=layers,
        state_gate_strength=state_gate_strength,
        state_target_weight=state_target_weight,
    )


def kg_state_gnn_propagate(
    graph: KnowledgeGraph,
    source: str,
    initial_fault: float,
    state_evidence: dict[str, float],
    params: StateKgGnnParameters,
) -> dict[str, float]:
    if source not in graph.nodes:
        raise KeyError(f"Unknown source node {source!r}")
    if params.layers < 0:
        raise ValueError("layers must be non-negative")

    scores = {source: float(initial_fault)}
    frontier = {source: float(initial_fault)}
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
                weight = _dynamic_edge_weight(params, triple.head, triple.relation, triple.tail, state_evidence)
                if weight is None:
                    continue
                next_frontier[triple.tail] = next_frontier.get(triple.tail, 0.0) + value * max(0.0, weight)

        if all(abs(value) <= EPSILON for value in next_frontier.values()):
            break
        for node, value in next_frontier.items():
            scores[node] = scores.get(node, 0.0) + value
        frontier = next_frontier
    return scores


def kg_state_gnn_root_scores(
    graph: KnowledgeGraph,
    case: StateKgGnnCase,
    variable_nodes: list[str],
    params: StateKgGnnParameters,
    candidates: list[str] | None = None,
    physical_initial_fault: float | None = None,
) -> list[tuple[str, float]]:
    if candidates is None:
        candidates = root_candidate_nodes(graph)
    target_nodes = [*variable_nodes, *state_target_nodes(variable_nodes)]
    target = _case_target_vector(case, variable_nodes, params)
    if physical_initial_fault is None:
        physical_initial_fault = max(case.contributions.values(), default=1.0)

    ranked: list[tuple[str, float]] = []
    for candidate in candidates:
        initial = case.contributions.get(candidate, physical_initial_fault)
        simulated = kg_state_gnn_propagate(graph, candidate, initial, case.state_evidence, params)
        vector = np.array([simulated.get(node, 0.0) for node in target_nodes], dtype=float)
        ranked.append((candidate, cosine_similarity(vector, target)))
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked


def kg_state_gnn_ranking_loss(
    graph: KnowledgeGraph,
    cases: Iterable[StateKgGnnCase],
    variable_nodes: list[str],
    params: StateKgGnnParameters,
    margin: float = 0.05,
    candidates: list[str] | None = None,
) -> float:
    losses: list[float] = []
    candidate_nodes = candidates or root_candidate_nodes(graph)
    for case in cases:
        positives = set(case.positive_nodes)
        case_candidates = list(dict.fromkeys([*candidate_nodes, *case.positive_nodes]))
        ranked = dict(kg_state_gnn_root_scores(graph, case, variable_nodes, params, case_candidates))
        positive_scores = [ranked[node] for node in case.positive_nodes if node in ranked]
        if not positive_scores:
            continue
        negative_scores = [score for node, score in ranked.items() if node not in positives]
        if not negative_scores:
            losses.extend(1.0 - score for score in positive_scores)
            continue
        hardest_negative = max(negative_scores)
        losses.extend(max(0.0, margin + hardest_negative - score) for score in positive_scores)
    if not losses:
        return 0.0
    return float(np.mean(losses))


def fit_state_kg_gnn_parameters_torch(
    graph: KnowledgeGraph,
    cases: Iterable[StateKgGnnCase],
    variable_nodes: list[str],
    params: StateKgGnnParameters,
    epochs: int = 300,
    learning_rate: float = 0.05,
    regularization: float = 0.01,
    device: str = "cuda",
    margin: float = 0.05,
) -> StateKgGnnTrainingResult:
    try:
        import torch
        import torch.nn.functional as functional
    except ImportError as exc:
        raise RuntimeError(
            "PyTorch is required for GPU KG-State-GNN training. Run with the configured pytorch environment."
        ) from exc

    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested, but torch.cuda.is_available() is false.")

    case_list = list(cases)
    if not case_list:
        return StateKgGnnTrainingResult(params=params, base_loss=0.0, final_loss=0.0, history=[0.0])

    torch_device = torch.device(device)
    node_names = list(graph.nodes)
    node_index = {node: index for index, node in enumerate(node_names)}
    candidate_nodes = root_candidate_nodes(graph)
    candidate_indices = torch.tensor([node_index[node] for node in candidate_nodes], dtype=torch.long, device=torch_device)
    target_nodes = [
        node
        for node in [*variable_nodes, *state_target_nodes(variable_nodes)]
        if node in node_index
    ]
    target_indices = torch.tensor([node_index[node] for node in target_nodes], dtype=torch.long, device=torch_device)

    triple_keys = [edge_key(triple.head, triple.relation, triple.tail) for triple in graph.triples]
    edge_heads = torch.tensor([node_index[triple.head] for triple in graph.triples], dtype=torch.long, device=torch_device)
    edge_tails = torch.tensor([node_index[triple.tail] for triple in graph.triples], dtype=torch.long, device=torch_device)
    base_edge_weights = torch.tensor(
        [
            float((params.edge_weights or {}).get(key, relation_prior_for_edge_key(key, params.relation_weights)))
            for key in triple_keys
        ],
        dtype=torch.float32,
        device=torch_device,
    )
    relation_priors = torch.tensor(
        [relation_prior_for_edge_key(key, params.relation_weights) for key in triple_keys],
        dtype=torch.float32,
        device=torch_device,
    )
    initial_raw = _torch_inverse_sigmoid(torch.clamp(base_edge_weights / 2.0, 1e-5, 1.0 - 1e-5))
    raw_weights = torch.nn.Parameter(initial_raw)
    optimizer = torch.optim.Adam([raw_weights], lr=learning_rate)

    prepared_cases = [
        _prepare_torch_state_case(
            case,
            variable_nodes,
            target_nodes,
            candidate_nodes,
            node_index,
            graph.triples,
            params.state_target_weight,
            torch_device,
        )
        for case in case_list
        if any(node in node_index for node in case.positive_nodes)
    ]
    if not prepared_cases:
        return StateKgGnnTrainingResult(params=params, base_loss=0.0, final_loss=0.0, history=[0.0])

    base_loss = kg_state_gnn_ranking_loss(graph, case_list, variable_nodes, params, margin=margin, candidates=candidate_nodes)
    history: list[float] = []
    for _ in range(max(0, epochs)):
        optimizer.zero_grad()
        ranking_loss, weights = _torch_state_ranking_loss(
            raw_weights,
            graph_node_count=len(node_names),
            candidate_indices=candidate_indices,
            target_indices=target_indices,
            edge_heads=edge_heads,
            edge_tails=edge_tails,
            prepared_cases=prepared_cases,
            layers=params.layers,
            self_weight=params.self_weight,
            state_gate_strength=params.state_gate_strength,
            margin=margin,
            torch_module=torch,
            functional=functional,
        )
        penalty = torch.mean((weights - base_edge_weights) ** 2)
        penalty = penalty + 0.25 * torch.mean((weights - relation_priors) ** 2)
        loss = ranking_loss + regularization * penalty
        loss.backward()
        optimizer.step()
        history.append(float(ranking_loss.detach().cpu()))

    final_weights = (2.0 * torch.sigmoid(raw_weights)).detach().cpu().numpy()
    edge_weight_map = {key: float(weight) for key, weight in zip(triple_keys, final_weights)}
    trained = StateKgGnnParameters(
        relation_weights=_average_relation_weights(graph, edge_weight_map),
        edge_weights=edge_weight_map,
        self_weight=params.self_weight,
        layers=params.layers,
        state_gate_strength=params.state_gate_strength,
        state_target_weight=params.state_target_weight,
    )
    final_loss = kg_state_gnn_ranking_loss(graph, case_list, variable_nodes, trained, margin=margin, candidates=candidate_nodes)
    return StateKgGnnTrainingResult(
        params=trained,
        base_loss=base_loss,
        final_loss=final_loss,
        history=history or [base_loss],
    )


def root_candidate_nodes(graph: KnowledgeGraph) -> list[str]:
    return [node for node in graph.nodes if not is_state_node(node) and graph.nodes[node].kind != "state"]


def _case_target_vector(
    case: StateKgGnnCase,
    variable_nodes: list[str],
    params: StateKgGnnParameters,
) -> np.ndarray:
    values = [case.contributions.get(variable, 0.0) for variable in variable_nodes]
    values.extend(
        params.state_target_weight * case.state_evidence.get(node, 0.0)
        for node in state_target_nodes(variable_nodes)
    )
    return np.array(values, dtype=float)


def _dynamic_edge_weight(
    params: StateKgGnnParameters,
    head: str,
    relation: str,
    tail: str,
    state_evidence: dict[str, float],
) -> float | None:
    if params.edge_weights is not None:
        key = edge_key(head, relation, tail)
        base = params.edge_weights.get(key)
    else:
        base = params.relation_weights.get(relation)
    if base is None:
        return None
    gate = 0.0
    if is_state_node(head):
        gate += state_evidence.get(head, 0.0)
    if is_state_node(tail):
        gate += state_evidence.get(tail, 0.0)
    return float(base) * (1.0 + params.state_gate_strength * gate)


def _prepare_torch_state_case(
    case: StateKgGnnCase,
    variable_nodes: list[str],
    target_nodes: list[str],
    candidate_nodes: list[str],
    node_index: dict[str, int],
    triples: list[object],
    state_target_weight: float,
    device: object,
) -> dict[str, object]:
    import torch

    physical_initial = max(case.contributions.values(), default=1.0)
    initial = [
        float(case.contributions.get(candidate, physical_initial))
        for candidate in candidate_nodes
    ]
    target = []
    variable_set = set(variable_nodes)
    for node in target_nodes:
        if node in variable_set:
            target.append(float(case.contributions.get(node, 0.0)))
        else:
            target.append(float(state_target_weight) * float(case.state_evidence.get(node, 0.0)))
    gate = []
    for triple in triples:
        value = 0.0
        if is_state_node(triple.head):
            value += case.state_evidence.get(triple.head, 0.0)
        if is_state_node(triple.tail):
            value += case.state_evidence.get(triple.tail, 0.0)
        gate.append(value)
    positive_candidate_positions = [
        index
        for index, candidate in enumerate(candidate_nodes)
        if candidate in set(case.positive_nodes)
    ]
    return {
        "initial": torch.tensor(initial, dtype=torch.float32, device=device),
        "target": torch.tensor(target, dtype=torch.float32, device=device),
        "edge_gate": torch.tensor(gate, dtype=torch.float32, device=device),
        "positive_positions": torch.tensor(positive_candidate_positions, dtype=torch.long, device=device),
    }


def _torch_state_ranking_loss(
    raw_weights: object,
    *,
    graph_node_count: int,
    candidate_indices: object,
    target_indices: object,
    edge_heads: object,
    edge_tails: object,
    prepared_cases: list[dict[str, object]],
    layers: int,
    self_weight: float,
    state_gate_strength: float,
    margin: float,
    torch_module: object,
    functional: object,
) -> tuple[object, object]:
    torch = torch_module
    weights = 2.0 * torch.sigmoid(raw_weights)
    losses = []
    candidate_count = int(candidate_indices.numel())
    row_indices = torch.arange(candidate_count, device=weights.device)

    for case in prepared_cases:
        positives = case["positive_positions"]
        if int(positives.numel()) == 0:
            continue
        dynamic_weights = weights * (1.0 + float(state_gate_strength) * case["edge_gate"])
        adjacency = torch.zeros((graph_node_count, graph_node_count), dtype=weights.dtype, device=weights.device)
        adjacency.index_put_((edge_heads, edge_tails), dynamic_weights, accumulate=True)

        frontier = torch.zeros((candidate_count, graph_node_count), dtype=weights.dtype, device=weights.device)
        frontier[row_indices, candidate_indices] = case["initial"]
        scores = frontier.clone()
        for _ in range(max(0, layers)):
            next_frontier = frontier @ adjacency
            if self_weight:
                next_frontier = next_frontier + frontier * float(self_weight)
            scores = scores + next_frontier
            frontier = next_frontier
        vectors = scores.index_select(1, target_indices)
        target = case["target"].reshape(1, -1)
        similarities = functional.cosine_similarity(vectors, target.expand_as(vectors), dim=1, eps=1e-12)
        negative_mask = torch.ones(candidate_count, dtype=torch.bool, device=weights.device)
        negative_mask[positives] = False
        if bool(negative_mask.any()):
            hardest_negative = similarities[negative_mask].max()
            losses.append(torch.relu(margin + hardest_negative - similarities[positives]))
        else:
            losses.append(1.0 - similarities[positives])

    if not losses:
        return torch.zeros((), dtype=weights.dtype, device=weights.device), weights
    return torch.cat([loss.reshape(-1) for loss in losses]).mean(), weights


def _add_edge_once(graph: KnowledgeGraph, head: str, relation: str, tail: str) -> None:
    if any(triple.head == head and triple.relation == relation and triple.tail == tail for triple in graph.outgoing(head)):
        return
    graph.add_edge(head, relation, tail)


def _safe_scale(values: np.ndarray) -> np.ndarray:
    return np.where(np.abs(values) <= EPSILON, 1.0, values)


def _positive_evidence(values: np.ndarray) -> np.ndarray:
    return np.clip(1.0 - np.exp(-np.maximum(values, 0.0)), 0.0, 1.0)


def _torch_inverse_sigmoid(value: object) -> object:
    import torch

    return torch.log(value / (1.0 - value))


def _average_relation_weights(graph: KnowledgeGraph, edge_weights: dict[str, float]) -> dict[str, float]:
    grouped: dict[str, list[float]] = {}
    for triple in graph.triples:
        key = edge_key(triple.head, triple.relation, triple.tail)
        grouped.setdefault(triple.relation, []).append(edge_weights[key])
    return {
        relation: float(np.mean(weights))
        for relation, weights in grouped.items()
    }
