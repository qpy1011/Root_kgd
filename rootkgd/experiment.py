from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

from .data import load_tep_fault, load_tep_normal
from .graph import KnowledgeGraph
from .rbc import fit_rbc_model, mean_fault_contribution
from .rfpa import root_scores
from .tep import build_tep_graph, tep_rfpa_parameters, tep_variable_nodes


@dataclass(frozen=True)
class PaperTarget:
    fault_id: int
    root_variables: tuple[str, ...]
    physical_roots: tuple[str, ...]
    description: str


@dataclass(frozen=True)
class CaseResult:
    fault_id: int
    n_components: int
    contributions: dict[str, float]
    ranked: list[tuple[str, float]]
    variable_rank: list[tuple[str, float]]
    physical_rank: list[tuple[str, float]]


def paper_targets() -> dict[int, PaperTarget]:
    return {
        1: PaperTarget(
            fault_id=1,
            root_variables=("x4", "x45"),
            physical_roots=("Stream 4",),
            description="A/C feed ratio step change in stream 4.",
        ),
        4: PaperTarget(
            fault_id=4,
            root_variables=("x51",),
            physical_roots=("Stream 12", "Reactor"),
            description="Reactor cooling-water inlet temperature step change.",
        ),
        6: PaperTarget(
            fault_id=6,
            root_variables=("x1", "x44"),
            physical_roots=("Stream 1",),
            description="A feed loss in stream 1.",
        ),
        12: PaperTarget(
            fault_id=12,
            root_variables=("x11",),
            physical_roots=("Stream 14", "Condenser", "Separator"),
            description="Condenser cooling-water inlet temperature random variation.",
        ),
    }


def fault_window(data: np.ndarray, start: int = 160, window: int = 100) -> np.ndarray:
    end = start + window
    if start < 0 or window <= 0 or end > data.shape[0]:
        raise ValueError(
            f"Invalid fault window start={start}, window={window} for {data.shape[0]} samples"
        )
    return data[start:end]


def top_by_kind(
    ranked: Iterable[tuple[str, float]],
    graph: KnowledgeGraph,
    kind: str,
    limit: int = 10,
) -> list[tuple[str, float]]:
    rows = [(node, score) for node, score in ranked if _matches_kind(graph.nodes[node].kind, kind)]
    return rows[:limit]


def _matches_kind(actual: str, expected: str) -> bool:
    if expected == "physical":
        return actual in {"physical", "device", "stream"}
    return actual == expected


def run_tep_case(
    data_dir: str | Path,
    fault_id: int,
    fault_start: int = 160,
    window: int = 100,
    principal_component_ratio: float = 0.5,
    top_n: int = 10,
) -> CaseResult:
    graph = build_tep_graph()
    variables = tep_variable_nodes()
    normal = load_tep_normal(data_dir)
    fault = load_tep_fault(data_dir, fault_id, testing=True)
    model = fit_rbc_model(normal, principal_component_ratio)
    samples = fault_window(fault, start=fault_start, window=window)
    contribution_array = mean_fault_contribution(samples, model)
    contributions = dict(zip(variables, map(float, contribution_array)))
    ranked = root_scores(graph, contributions, variables, tep_rfpa_parameters())
    return CaseResult(
        fault_id=fault_id,
        n_components=model.n_components,
        contributions=contributions,
        ranked=ranked,
        variable_rank=top_by_kind(ranked, graph, "variable", top_n),
        physical_rank=top_by_kind(ranked, graph, "physical", top_n),
    )


def run_tep_reproduction(
    data_dir: str | Path,
    fault_ids: Iterable[int] = (1, 4, 6, 12),
    output_dir: str | Path = "outputs",
    fault_start: int = 160,
    window: int = 100,
    principal_component_ratio: float = 0.5,
) -> list[CaseResult]:
    results = [
        run_tep_case(
            data_dir=data_dir,
            fault_id=fault_id,
            fault_start=fault_start,
            window=window,
            principal_component_ratio=principal_component_ratio,
        )
        for fault_id in fault_ids
    ]
    write_results(results, output_dir)
    return results


def write_results(results: Iterable[CaseResult], output_dir: str | Path) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    targets = paper_targets()
    summary: list[dict[str, object]] = []

    for result in results:
        prefix = output / f"idv{result.fault_id:02d}"
        _write_rank_csv(prefix.with_name(prefix.name + "_variables.csv"), result.variable_rank)
        _write_rank_csv(prefix.with_name(prefix.name + "_physical.csv"), result.physical_rank)
        _write_rank_csv(
            prefix.with_name(prefix.name + "_rbc_contribution.csv"),
            sorted(result.contributions.items(), key=lambda item: item[1], reverse=True),
        )

        target = targets.get(result.fault_id)
        summary.append(_case_summary(result, target))

    with (output / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)


def _write_rank_csv(path: Path, rows: Iterable[tuple[str, float]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["rank", "node", "score"])
        for rank, (node, score) in enumerate(rows, start=1):
            writer.writerow([rank, node, f"{score:.12g}"])


def _case_summary(result: CaseResult, target: PaperTarget | None) -> dict[str, object]:
    variable_positions = _rank_positions(result.variable_rank)
    physical_positions = _rank_positions(result.physical_rank)
    if target is None:
        return {
            "fault_id": result.fault_id,
            "n_components": result.n_components,
            "top_variable": result.variable_rank[0][0] if result.variable_rank else None,
            "top_physical": result.physical_rank[0][0] if result.physical_rank else None,
        }

    return {
        "fault_id": result.fault_id,
        "description": target.description,
        "n_components": result.n_components,
        "expected_variables": target.root_variables,
        "expected_physical": target.physical_roots,
        "top_variable": result.variable_rank[0][0] if result.variable_rank else None,
        "top_physical": result.physical_rank[0][0] if result.physical_rank else None,
        "expected_variable_ranks": {
            node: variable_positions.get(node) for node in target.root_variables
        },
        "expected_physical_ranks": {
            node: physical_positions.get(node) for node in target.physical_roots
        },
    }


def _rank_positions(rows: list[tuple[str, float]]) -> dict[str, int]:
    return {node: index for index, (node, _) in enumerate(rows, start=1)}
