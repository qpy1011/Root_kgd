from __future__ import annotations

from .graph import KnowledgeGraph
from .rfpa import RfpaParameters


def tep_variable_nodes() -> list[str]:
    return [f"x{i}" for i in range(1, 53)]


def tep_rfpa_parameters(max_starts: int = 1, min_delta: float = 1e-8) -> RfpaParameters:
    return RfpaParameters(
        distances={
            "State": 1,
            "State of": 1,
            "Output": 3,
            "Contain": 5,
            "Contained by": 5,
            "Generate": 20,
        },
        priorities={
            "State": 1,
            "State of": 1,
            "Output": 5,
            "Contain": 8,
            "Contained by": 8,
            "Generate": 20,
        },
        sigma=0.1,
        max_starts=max_starts,
        min_delta=min_delta,
    )


def build_tep_graph() -> KnowledgeGraph:
    graph = KnowledgeGraph()

    for node in tep_variable_nodes():
        graph.add_node(node, "variable")

    devices = ["Reactor", "Separator", "Stripper", "Condenser", "Compressor"]
    streams = [f"Stream {i}" for i in range(1, 15)] + ["Stripper Steam"]
    substances = list("ABCDEFGH") + ["Cooling Water", "Steam"]
    for node in devices:
        graph.add_node(node, "device")
    for node in streams:
        graph.add_node(node, "stream")
    for node in substances:
        graph.add_node(node, "substance")

    for physical, variable in _variable_state_pairs():
        _add_state(graph, physical, variable)

    for head, tail in _process_outputs():
        graph.add_edge(head, "Output", tail)

    for container, substance in _containment_pairs():
        graph.add_edge(container, "Contain", substance)
        graph.add_edge(substance, "Contained by", container)

    for reactant, product in _generation_pairs():
        graph.add_edge(reactant, "Generate", product)

    return graph


def _add_state(graph: KnowledgeGraph, physical: str, variable: str) -> None:
    graph.add_edge(physical, "State", variable)
    graph.add_edge(variable, "State of", physical)


def _variable_state_pairs() -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = [
        ("Stream 1", "x1"),
        ("Stream 2", "x2"),
        ("Stream 3", "x3"),
        ("Stream 4", "x4"),
        ("Stream 8", "x5"),
        ("Stream 6", "x6"),
        ("Reactor", "x7"),
        ("Reactor", "x8"),
        ("Reactor", "x9"),
        ("Stream 9", "x10"),
        ("Separator", "x11"),
        ("Stream 14", "x11"),
        ("Separator", "x12"),
        ("Separator", "x13"),
        ("Stream 10", "x14"),
        ("Stripper", "x15"),
        ("Stripper", "x16"),
        ("Stream 11", "x17"),
        ("Stripper", "x18"),
        ("Stripper", "x19"),
        ("Stripper Steam", "x19"),
        ("Compressor", "x20"),
        ("Reactor", "x21"),
        ("Stream 12", "x21"),
        ("Condenser", "x22"),
        ("Stream 13", "x22"),
        ("Stream 6", "x23"),
        ("Stream 6", "x24"),
        ("Stream 6", "x25"),
        ("Stream 6", "x26"),
        ("Stream 6", "x27"),
        ("Stream 6", "x28"),
        ("Stream 9", "x29"),
        ("Stream 9", "x30"),
        ("Stream 9", "x31"),
        ("Stream 9", "x32"),
        ("Stream 9", "x33"),
        ("Stream 9", "x34"),
        ("Stream 9", "x35"),
        ("Stream 9", "x36"),
        ("Stream 11", "x37"),
        ("Stream 11", "x38"),
        ("Stream 11", "x39"),
        ("Stream 11", "x40"),
        ("Stream 11", "x41"),
        ("Stream 2", "x42"),
        ("Stream 3", "x43"),
        ("Stream 1", "x44"),
        ("Stream 4", "x45"),
        ("Compressor", "x46"),
        ("Stream 8", "x46"),
        ("Stream 9", "x47"),
        ("Separator", "x48"),
        ("Stream 10", "x48"),
        ("Stripper", "x49"),
        ("Stream 11", "x49"),
        ("Stripper", "x50"),
        ("Stripper Steam", "x50"),
        ("Reactor", "x51"),
        ("Stream 12", "x51"),
        ("Condenser", "x52"),
        ("Stream 13", "x52"),
    ]

    component_streams = {
        "x23": "A",
        "x24": "B",
        "x25": "C",
        "x26": "D",
        "x27": "E",
        "x28": "F",
        "x29": "A",
        "x30": "B",
        "x31": "C",
        "x32": "D",
        "x33": "E",
        "x34": "F",
        "x35": "G",
        "x36": "H",
        "x37": "D",
        "x38": "E",
        "x39": "F",
        "x40": "G",
        "x41": "H",
    }
    pairs.extend((substance, variable) for variable, substance in component_streams.items())
    return pairs


def _process_outputs() -> list[tuple[str, str]]:
    return [
        ("Stream 1", "Stream 6"),
        ("Stream 2", "Stream 6"),
        ("Stream 3", "Stream 6"),
        ("Stream 4", "Stripper"),
        ("Stream 8", "Stream 6"),
        ("Stream 6", "Reactor"),
        ("Reactor", "Stream 7"),
        ("Stream 7", "Condenser"),
        ("Condenser", "Stream 14"),
        ("Stream 14", "Separator"),
        ("Separator", "Stream 8"),
        ("Separator", "Stream 9"),
        ("Separator", "Stream 10"),
        ("Stream 8", "Compressor"),
        ("Compressor", "Stream 6"),
        ("Stream 5", "Stream 6"),
        ("Stream 10", "Stripper"),
        ("Stripper", "Stream 11"),
        ("Stripper", "Stream 5"),
        ("Stripper Steam", "Stripper"),
        ("Stream 12", "Reactor"),
        ("Stream 13", "Condenser"),
    ]


def _containment_pairs() -> list[tuple[str, str]]:
    return [
        ("Stream 1", "A"),
        ("Stream 2", "D"),
        ("Stream 3", "E"),
        ("Stream 4", "A"),
        ("Stream 4", "B"),
        ("Stream 4", "C"),
        ("Stream 5", "A"),
        ("Stream 5", "B"),
        ("Stream 5", "C"),
        ("Stream 5", "D"),
        ("Stream 5", "E"),
        ("Stream 5", "F"),
        ("Stream 5", "G"),
        ("Stream 5", "H"),
        ("Stream 6", "A"),
        ("Stream 6", "B"),
        ("Stream 6", "C"),
        ("Stream 6", "D"),
        ("Stream 6", "E"),
        ("Stream 6", "F"),
        ("Stream 7", "A"),
        ("Stream 7", "B"),
        ("Stream 7", "C"),
        ("Stream 7", "D"),
        ("Stream 7", "E"),
        ("Stream 7", "F"),
        ("Stream 7", "G"),
        ("Stream 7", "H"),
        ("Stream 8", "A"),
        ("Stream 8", "B"),
        ("Stream 8", "C"),
        ("Stream 8", "D"),
        ("Stream 8", "E"),
        ("Stream 8", "F"),
        ("Stream 8", "G"),
        ("Stream 8", "H"),
        ("Stream 9", "A"),
        ("Stream 9", "B"),
        ("Stream 9", "C"),
        ("Stream 9", "D"),
        ("Stream 9", "E"),
        ("Stream 9", "F"),
        ("Stream 9", "G"),
        ("Stream 9", "H"),
        ("Stream 10", "D"),
        ("Stream 10", "E"),
        ("Stream 10", "F"),
        ("Stream 10", "G"),
        ("Stream 10", "H"),
        ("Stream 11", "D"),
        ("Stream 11", "E"),
        ("Stream 11", "F"),
        ("Stream 11", "G"),
        ("Stream 11", "H"),
        ("Stream 12", "Cooling Water"),
        ("Stream 13", "Cooling Water"),
        ("Stream 14", "A"),
        ("Stream 14", "B"),
        ("Stream 14", "C"),
        ("Stream 14", "D"),
        ("Stream 14", "E"),
        ("Stream 14", "F"),
        ("Stream 14", "G"),
        ("Stream 14", "H"),
        ("Stripper Steam", "Steam"),
    ]


def _generation_pairs() -> list[tuple[str, str]]:
    return [
        ("A", "G"),
        ("C", "G"),
        ("D", "G"),
        ("A", "H"),
        ("C", "H"),
        ("E", "H"),
        ("A", "F"),
        ("D", "F"),
        ("E", "F"),
    ]
