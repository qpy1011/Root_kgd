from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from rootkgd.experiment import paper_targets, run_tep_case, top_by_kind
from rootkgd.gnn import (
    fit_gnn_parameters,
    fit_gnn_parameters_torch,
    gnn_ranking_loss,
    gnn_root_scores,
    initial_gnn_parameters_from_rfpa,
    make_training_cases_from_targets,
    with_edge_weights_from_graph,
)
from rootkgd.tep import build_tep_graph, tep_rfpa_parameters, tep_variable_nodes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the TEP GNN-Root-KGD experiment.")
    parser.add_argument(
        "--data-dir",
        default="tennessee-eastman-profBraatz-master",
        help="Directory containing d00.dat and dXX_te.dat files.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs_gnn",
        help="Directory for GNN ranking outputs.",
    )
    parser.add_argument(
        "--faults",
        nargs="+",
        type=int,
        default=list(range(1, 22)),
        help="TEP IDV fault numbers to run.",
    )
    parser.add_argument("--fault-start", type=int, default=160)
    parser.add_argument("--window", type=int, default=100)
    parser.add_argument("--r-pc", type=float, default=0.56)
    parser.add_argument("--layers", type=int, default=5)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--regularization", type=float, default=0.01)
    parser.add_argument(
        "--backend",
        choices=["auto", "numpy", "torch"],
        default="auto",
        help="Training backend. auto uses torch+CUDA when available, otherwise NumPy.",
    )
    parser.add_argument("--device", default="cuda", help="Torch device, e.g. cuda or cpu.")
    parser.add_argument("--torch-epochs", type=int, default=1000)
    parser.add_argument("--torch-lr", type=float, default=0.01)
    parser.add_argument(
        "--edge-epochs",
        type=int,
        default=30,
        help="Fine-tuning epochs for edge-specific weights after relation-level pretraining.",
    )
    parser.add_argument(
        "--max-trainable-edges",
        type=int,
        default=120,
        help="Maximum number of edge-specific weights to update; all other edges keep RFPA-prior weights.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    backend = _resolve_backend(args.backend, args.device)
    graph = build_tep_graph()
    variables = tep_variable_nodes()
    targets = paper_targets()
    rfpa_params = tep_rfpa_parameters()
    relations = sorted({triple.relation for triple in graph.triples})
    base_params = initial_gnn_parameters_from_rfpa(
        relations,
        rfpa_params.distances,
        rfpa_params.sigma,
        layers=args.layers,
    )

    case_results = [
        run_tep_case(
            data_dir=Path(args.data_dir),
            fault_id=fault_id,
            fault_start=args.fault_start,
            window=args.window,
            principal_component_ratio=args.r_pc,
        )
        for fault_id in args.faults
    ]
    training_cases = make_training_cases_from_targets(case_results, targets)
    relation_training_result = None
    if backend == "torch":
        edge_base_params = initial_gnn_parameters_from_rfpa(
            relations,
            rfpa_params.distances,
            rfpa_params.sigma,
            layers=args.layers,
            graph=graph,
        )
        training_result = fit_gnn_parameters_torch(
            graph,
            training_cases,
            variables,
            edge_base_params,
            epochs=args.torch_epochs,
            learning_rate=args.torch_lr,
            regularization=args.regularization,
            device=args.device,
        )
    else:
        relation_training_result = fit_gnn_parameters(
            graph,
            training_cases,
            variables,
            base_params,
            epochs=args.epochs,
            regularization=args.regularization,
            max_trainable_edges=0,
        )
        edge_base_params = with_edge_weights_from_graph(graph, relation_training_result.params)
        training_result = fit_gnn_parameters(
            graph,
            training_cases,
            variables,
            edge_base_params,
            epochs=args.edge_epochs,
            regularization=args.regularization,
            max_trainable_edges=args.max_trainable_edges,
        )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = []
    for result in case_results:
        ranked = gnn_root_scores(
            graph,
            result.contributions,
            variables,
            training_result.params,
        )
        variable_rank = top_by_kind(ranked, graph, "variable", limit=10)
        physical_rank = top_by_kind(ranked, graph, "physical", limit=10)
        prefix = output_dir / f"idv{result.fault_id:02d}_gnn"
        _write_rank_csv(prefix.with_name(prefix.name + "_all.csv"), ranked[:25])
        _write_rank_csv(prefix.with_name(prefix.name + "_variables.csv"), variable_rank)
        _write_rank_csv(prefix.with_name(prefix.name + "_physical.csv"), physical_rank)
        summary.append(_case_summary(result.fault_id, targets.get(result.fault_id), variable_rank, physical_rank))

    _write_relation_weights(output_dir / "relation_weights.csv", training_result.params.relation_weights)
    _write_edge_weights(output_dir / "edge_weights.csv", training_result.params.edge_weights or {})
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "base_loss": training_result.base_loss,
                "final_loss": training_result.final_loss,
                "backend": backend,
                "device": args.device if backend == "torch" else "cpu",
                "torch_epochs": args.torch_epochs if backend == "torch" else None,
                "torch_lr": args.torch_lr if backend == "torch" else None,
                "relation_base_loss": relation_training_result.base_loss if relation_training_result else None,
                "relation_final_loss": relation_training_result.final_loss if relation_training_result else None,
                "check_loss": gnn_ranking_loss(
                    graph,
                    training_cases,
                    variables,
                    training_result.params,
                ),
                "layers": training_result.params.layers,
                "history": training_result.history,
                "relation_weights": training_result.params.relation_weights,
                "edge_weight_count": len(training_result.params.edge_weights or {}),
                "edge_weights_file": "edge_weights.csv",
                "max_trainable_edges": args.max_trainable_edges,
                "evaluation": _evaluation_metrics(summary),
                "cases": summary,
            },
            handle,
            indent=2,
        )

    print(
        f"GNN({backend}) loss {training_result.base_loss:.6f} -> {training_result.final_loss:.6f}; "
        f"wrote outputs to {output_dir.resolve()}"
    )
    for row in summary:
        print(
            f"IDV({row['fault_id']}) top variable {row['top_variable']} | "
            f"top physical {row['top_physical']}"
        )


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


def _resolve_backend(requested: str, device: str) -> str:
    if requested != "auto":
        return requested
    try:
        import torch
    except ImportError:
        return "numpy"
    if device == "cuda" and not torch.cuda.is_available():
        return "numpy"
    return "torch"


if __name__ == "__main__":
    main()
