from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from rootkgd.experiment import paper_targets, run_tep_case, top_by_kind
from rootkgd.gnn import (
    fit_gnn_parameters,
    gnn_ranking_loss,
    gnn_root_scores,
    initial_gnn_parameters_from_rfpa,
    make_training_cases_from_targets,
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
        default=[1, 4, 6, 12],
        help="TEP IDV fault numbers to run.",
    )
    parser.add_argument("--fault-start", type=int, default=160)
    parser.add_argument("--window", type=int, default=100)
    parser.add_argument("--r-pc", type=float, default=0.56)
    parser.add_argument("--layers", type=int, default=6)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--regularization", type=float, default=0.01)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
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
    training_result = fit_gnn_parameters(
        graph,
        training_cases,
        variables,
        base_params,
        epochs=args.epochs,
        regularization=args.regularization,
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
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "base_loss": training_result.base_loss,
                "final_loss": training_result.final_loss,
                "check_loss": gnn_ranking_loss(
                    graph,
                    training_cases,
                    variables,
                    training_result.params,
                ),
                "layers": training_result.params.layers,
                "history": training_result.history,
                "relation_weights": training_result.params.relation_weights,
                "cases": summary,
            },
            handle,
            indent=2,
        )

    print(
        f"GNN loss {training_result.base_loss:.6f} -> {training_result.final_loss:.6f}; "
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


def _rank_positions(rows: list[tuple[str, float]]) -> dict[str, int]:
    return {node: index for index, (node, _) in enumerate(rows, start=1)}


if __name__ == "__main__":
    main()
