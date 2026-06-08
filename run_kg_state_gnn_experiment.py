from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from rootkgd.data import load_tep_fault, load_tep_normal
from rootkgd.experiment import fault_window, paper_targets, top_by_kind
from rootkgd.kg_state_gnn import (
    STATE_BACK_RELATION,
    STATE_RELATION,
    StateKgGnnCase,
    augment_graph_with_state_nodes,
    compute_state_evidence,
    fit_state_kg_gnn_parameters_torch,
    initial_state_kg_gnn_parameters,
    kg_state_gnn_ranking_loss,
    kg_state_gnn_root_scores,
)
from rootkgd.rbc import fit_rbc_model, mean_fault_contribution
from rootkgd.tep import build_tep_graph, tep_rfpa_parameters, tep_variable_nodes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the TEP knowledge-graph state adaptive GNN experiment."
    )
    parser.add_argument(
        "--data-dir",
        default="tennessee-eastman-profBraatz-master",
        help="Directory containing d00.dat and dXX_te.dat files.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs_kg_state_gnn",
        help="Directory for KG-State-GNN ranking outputs.",
    )
    parser.add_argument("--faults", nargs="+", type=int, default=list(range(1, 22)))
    parser.add_argument("--fault-start", type=int, default=160)
    parser.add_argument("--window", type=int, default=100)
    parser.add_argument("--r-pc", type=float, default=0.56)
    parser.add_argument("--layers", type=int, default=5)
    parser.add_argument("--regularization", type=float, default=0.01)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--torch-epochs", type=int, default=1000)
    parser.add_argument("--torch-lr", type=float, default=0.01)
    parser.add_argument("--state-gate-strength", type=float, default=1.0)
    parser.add_argument("--state-target-weight", type=float, default=0.2)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    variables = tep_variable_nodes()
    base_graph = build_tep_graph()
    graph = augment_graph_with_state_nodes(base_graph, variables)
    rfpa_params = tep_rfpa_parameters()
    relation_weights = _initial_relation_weights(
        {triple.relation for triple in graph.triples},
        rfpa_params.distances,
        rfpa_params.sigma,
    )
    params = initial_state_kg_gnn_parameters(
        graph,
        relation_weights,
        layers=args.layers,
        state_gate_strength=args.state_gate_strength,
        state_target_weight=args.state_target_weight,
    )
    case_payloads, training_cases = _build_cases(
        data_dir=Path(args.data_dir),
        fault_ids=args.faults,
        variables=variables,
        fault_start=args.fault_start,
        window=args.window,
        principal_component_ratio=args.r_pc,
    )
    training_result = fit_state_kg_gnn_parameters_torch(
        graph,
        training_cases,
        variables,
        params,
        epochs=args.torch_epochs,
        learning_rate=args.torch_lr,
        regularization=args.regularization,
        device=args.device,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    targets = paper_targets()
    summary = []
    for payload in case_payloads:
        case = payload["case"]
        fault_id = payload["fault_id"]
        ranked = kg_state_gnn_root_scores(
            graph,
            case,
            variables,
            training_result.params,
        )
        variable_rank = top_by_kind(ranked, graph, "variable", limit=10)
        physical_rank = top_by_kind(ranked, graph, "physical", limit=10)
        prefix = output_dir / f"idv{fault_id:02d}_kg_state_gnn"
        _write_rank_csv(prefix.with_name(prefix.name + "_all.csv"), ranked[:25])
        _write_rank_csv(prefix.with_name(prefix.name + "_variables.csv"), variable_rank)
        _write_rank_csv(prefix.with_name(prefix.name + "_physical.csv"), physical_rank)
        _write_rank_csv(
            prefix.with_name(prefix.name + "_state_evidence.csv"),
            sorted(case.state_evidence.items(), key=lambda item: item[1], reverse=True)[:25],
        )
        summary.append(_case_summary(fault_id, targets.get(fault_id), variable_rank, physical_rank))

    _write_relation_weights(output_dir / "relation_weights.csv", training_result.params.relation_weights)
    _write_edge_weights(output_dir / "edge_weights.csv", training_result.params.edge_weights or {})
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "model": "KG-State-GNN",
                "base_loss": training_result.base_loss,
                "final_loss": training_result.final_loss,
                "check_loss": kg_state_gnn_ranking_loss(
                    graph,
                    training_cases,
                    variables,
                    training_result.params,
                ),
                "device": args.device,
                "torch_epochs": args.torch_epochs,
                "torch_lr": args.torch_lr,
                "layers": training_result.params.layers,
                "state_gate_strength": training_result.params.state_gate_strength,
                "state_target_weight": training_result.params.state_target_weight,
                "history": training_result.history,
                "node_count": len(graph.nodes),
                "edge_count": len(graph.triples),
                "edge_weight_count": len(training_result.params.edge_weights or {}),
                "evaluation": _evaluation_metrics(summary),
                "cases": summary,
            },
            handle,
            indent=2,
        )

    print(
        f"KG-State-GNN loss {training_result.base_loss:.6f} -> {training_result.final_loss:.6f}; "
        f"wrote outputs to {output_dir.resolve()}"
    )
    for row in summary:
        print(
            f"IDV({row['fault_id']}) top variable {row['top_variable']} | "
            f"top physical {row['top_physical']}"
        )


def _build_cases(
    *,
    data_dir: Path,
    fault_ids: list[int],
    variables: list[str],
    fault_start: int,
    window: int,
    principal_component_ratio: float,
) -> tuple[list[dict[str, object]], list[StateKgGnnCase]]:
    normal = load_tep_normal(data_dir)
    model = fit_rbc_model(normal, principal_component_ratio)
    targets = paper_targets()
    payloads: list[dict[str, object]] = []
    cases: list[StateKgGnnCase] = []
    for fault_id in fault_ids:
        fault = load_tep_fault(data_dir, fault_id, testing=True)
        samples = fault_window(fault, start=fault_start, window=window)
        contribution_array = mean_fault_contribution(samples, model)
        contributions = dict(zip(variables, map(float, contribution_array)))
        state_evidence = compute_state_evidence(normal, samples, variables)
        target = targets.get(fault_id)
        positive_nodes = tuple(target.root_variables + target.physical_roots) if target else ()
        case = StateKgGnnCase(
            name=f"IDV({fault_id})",
            contributions=contributions,
            state_evidence=state_evidence,
            positive_nodes=positive_nodes,
        )
        payloads.append({"fault_id": fault_id, "case": case})
        if positive_nodes:
            cases.append(case)
    return payloads, cases


def _initial_relation_weights(
    relations: set[str],
    rfpa_distances: dict[str, float],
    sigma: float,
) -> dict[str, float]:
    weights = {
        relation: float(np.exp(-sigma * rfpa_distances.get(relation, 1.0)))
        for relation in sorted(relations)
    }
    weights[STATE_RELATION] = 1.0
    weights[STATE_BACK_RELATION] = 1.0
    return weights


def _case_summary(
    fault_id: int,
    target: object | None,
    variable_rank: list[tuple[str, float]],
    physical_rank: list[tuple[str, float]],
) -> dict[str, object]:
    variable_positions = _rank_positions(variable_rank)
    physical_positions = _rank_positions(physical_rank)
    if target is None:
        return {
            "fault_id": fault_id,
            "top_variable": variable_rank[0][0] if variable_rank else None,
            "top_physical": physical_rank[0][0] if physical_rank else None,
        }
    return {
        "fault_id": fault_id,
        "description": target.description,
        "label_source": target.label_source,
        "expected_variables": target.root_variables,
        "expected_physical": target.physical_roots,
        "top_variable": variable_rank[0][0] if variable_rank else None,
        "top_physical": physical_rank[0][0] if physical_rank else None,
        "expected_variable_ranks": {
            node: variable_positions.get(node) for node in target.root_variables
        },
        "expected_physical_ranks": {
            node: physical_positions.get(node) for node in target.physical_roots
        },
    }


def _write_rank_csv(path: Path, rows: list[tuple[str, float]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["rank", "node", "score"])
        for rank, (node, score) in enumerate(rows, start=1):
            writer.writerow([rank, node, f"{score:.12g}"])


def _write_relation_weights(path: Path, weights: dict[str, float]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["relation", "weight"])
        for relation, weight in sorted(weights.items()):
            writer.writerow([relation, f"{weight:.12g}"])


def _write_edge_weights(path: Path, weights: dict[str, float]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["head", "relation", "tail", "edge_key", "weight"])
        for key, weight in sorted(weights.items()):
            head, relation, tail = _split_edge_key(key)
            writer.writerow([head, relation, tail, key, f"{weight:.12g}"])


def _split_edge_key(key: str) -> tuple[str, str, str]:
    parts = key.split("|", 2)
    if len(parts) != 3:
        return key, "", ""
    return parts[0], parts[1], parts[2]


def _rank_positions(rows: list[tuple[str, float]]) -> dict[str, int]:
    return {node: index for index, (node, _) in enumerate(rows, start=1)}


def _evaluation_metrics(cases: list[dict[str, object]]) -> dict[str, int]:
    metrics = {
        "case_count": len(cases),
        "variable_top1": 0,
        "variable_top3": 0,
        "physical_top1": 0,
        "physical_top3": 0,
    }
    for case in cases:
        variable_ranks = _valid_ranks(case.get("expected_variable_ranks", {}))
        physical_ranks = _valid_ranks(case.get("expected_physical_ranks", {}))
        if variable_ranks:
            best = min(variable_ranks)
            metrics["variable_top1"] += int(best == 1)
            metrics["variable_top3"] += int(best <= 3)
        if physical_ranks:
            best = min(physical_ranks)
            metrics["physical_top1"] += int(best == 1)
            metrics["physical_top3"] += int(best <= 3)
    return metrics


def _valid_ranks(value: object) -> list[int]:
    if not isinstance(value, dict):
        return []
    return [rank for rank in value.values() if isinstance(rank, int)]


if __name__ == "__main__":
    main()
