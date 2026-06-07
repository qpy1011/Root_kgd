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
    label_source: str = "paper"


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
        2: PaperTarget(
            fault_id=2,
            root_variables=("x24",),
            physical_roots=("Stream 4",),
            description="B composition step change in stream 4, with A/C ratio constant.",
            label_source="TEP disturbance table + PIKG approximation",
        ),
        3: PaperTarget(
            fault_id=3,
            root_variables=("x2", "x42"),
            physical_roots=("Stream 2",),
            description="D feed temperature step change in stream 2.",
            label_source="TEP disturbance table + closest observable flow variables",
        ),
        4: PaperTarget(
            fault_id=4,
            root_variables=("x51",),
            physical_roots=("Stream 12", "Reactor"),
            description="Reactor cooling-water inlet temperature step change.",
        ),
        5: PaperTarget(
            fault_id=5,
            root_variables=("x22", "x52"),
            physical_roots=("Stream 13", "Condenser"),
            description="Condenser cooling-water inlet temperature step change.",
            label_source="TEP disturbance table + closest observable cooling-water variables",
        ),
        6: PaperTarget(
            fault_id=6,
            root_variables=("x1", "x44"),
            physical_roots=("Stream 1",),
            description="A feed loss in stream 1.",
        ),
        7: PaperTarget(
            fault_id=7,
            root_variables=("x4", "x45"),
            physical_roots=("Stream 4",),
            description="C header pressure loss / reduced availability in stream 4.",
            label_source="TEP disturbance table + closest observable stream-4 variables",
        ),
        8: PaperTarget(
            fault_id=8,
            root_variables=("x23", "x24", "x25"),
            physical_roots=("Stream 4",),
            description="A, B, C feed composition random variation in stream 4.",
            label_source="TEP disturbance table + reactor-feed composition variables",
        ),
        9: PaperTarget(
            fault_id=9,
            root_variables=("x2", "x42"),
            physical_roots=("Stream 2",),
            description="D feed temperature random variation in stream 2.",
            label_source="TEP disturbance table + closest observable flow variables",
        ),
        10: PaperTarget(
            fault_id=10,
            root_variables=("x25",),
            physical_roots=("Stream 4",),
            description="C feed temperature random variation in stream 4.",
            label_source="TEP disturbance table + closest observable component variable",
        ),
        11: PaperTarget(
            fault_id=11,
            root_variables=("x21", "x51"),
            physical_roots=("Stream 12", "Reactor"),
            description="Reactor cooling-water inlet temperature random variation.",
            label_source="TEP disturbance table + cooling-water variables",
        ),
        12: PaperTarget(
            fault_id=12,
            root_variables=("x11",),
            physical_roots=("Stream 14", "Condenser", "Separator"),
            description="Condenser cooling-water inlet temperature random variation.",
        ),
        13: PaperTarget(
            fault_id=13,
            root_variables=("x9",),
            physical_roots=("Reactor",),
            description="Reaction kinetics slow drift.",
            label_source="TEP disturbance table + reactor state approximation",
        ),
        14: PaperTarget(
            fault_id=14,
            root_variables=("x51",),
            physical_roots=("Stream 12", "Reactor"),
            description="Reactor cooling-water valve sticking.",
            label_source="TEP disturbance table + XMV(10)",
        ),
        15: PaperTarget(
            fault_id=15,
            root_variables=("x52",),
            physical_roots=("Stream 13", "Condenser"),
            description="Condenser cooling-water valve sticking.",
            label_source="TEP disturbance table + XMV(11)",
        ),
        16: PaperTarget(
            fault_id=16,
            root_variables=("x19", "x50"),
            physical_roots=("Stripper Steam", "Stripper"),
            description="Unknown disturbance; source code maps it to stripper heat-transfer / steam-side random walk.",
            label_source="weak label from teprob.f TESUB8(9)",
        ),
        17: PaperTarget(
            fault_id=17,
            root_variables=("x21", "x51"),
            physical_roots=("Stream 12", "Reactor"),
            description="Unknown disturbance; source code maps it to reactor cooling heat-transfer random walk.",
            label_source="weak label from teprob.f TESUB8(10)",
        ),
        18: PaperTarget(
            fault_id=18,
            root_variables=("x22", "x52"),
            physical_roots=("Stream 13", "Condenser"),
            description="Unknown disturbance; source code maps it to separator/condenser cooling heat-transfer random walk.",
            label_source="weak label from teprob.f TESUB8(11)",
        ),
        19: PaperTarget(
            fault_id=19,
            root_variables=("x46", "x48", "x49", "x50"),
            physical_roots=("Compressor", "Separator", "Stripper", "Stripper Steam"),
            description="Unknown disturbance; source code applies valve stiction to XMV(5), XMV(7), XMV(8), and XMV(9).",
            label_source="weak label from teprob.f IVST mappings",
        ),
        20: PaperTarget(
            fault_id=20,
            root_variables=("x5", "x46"),
            physical_roots=("Stream 8", "Compressor"),
            description="Unknown disturbance; source code maps it to stream-8/recycle flow random walk.",
            label_source="weak label from teprob.f TESUB8(12)",
        ),
        21: PaperTarget(
            fault_id=21,
            root_variables=("x4", "x45"),
            physical_roots=("Stream 4",),
            description="Stream-4 valve position held constant at steady-state position.",
            label_source="weak label from external TEP 21-fault convention",
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
        "label_source": target.label_source,
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
