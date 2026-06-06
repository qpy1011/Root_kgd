import numpy as np

from rootkgd.experiment import fault_window, paper_targets, top_by_kind
from rootkgd.graph import KnowledgeGraph


def test_fault_window_selects_first_fault_samples_after_start() -> None:
    data = np.arange(20).reshape(10, 2)

    selected = fault_window(data, start=3, window=4)

    assert selected.shape == (4, 2)
    np.testing.assert_array_equal(selected, data[3:7])


def test_top_by_kind_filters_ranked_nodes() -> None:
    graph = KnowledgeGraph()
    graph.add_node("x1", "variable")
    graph.add_node("Stream 1", "stream")
    graph.add_node("A", "substance")
    graph.add_node("x2", "variable")
    ranked = [("A", 0.95), ("Stream 1", 0.9), ("x1", 0.8), ("x2", 0.7)]

    assert top_by_kind(ranked, graph, "variable", limit=1) == [("x1", 0.8)]
    assert top_by_kind(ranked, graph, "physical", limit=1) == [("Stream 1", 0.9)]


def test_paper_targets_cover_tep_cases() -> None:
    targets = paper_targets()

    assert targets[1].root_variables == ("x4", "x45")
    assert targets[4].root_variables == ("x51",)
    assert targets[6].root_variables == ("x1", "x44")
    assert targets[12].root_variables == ("x11",)
