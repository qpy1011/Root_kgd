import numpy as np

from rootkgd.gnn import (
    GnnParameters,
    GnnTrainingCase,
    fit_gnn_parameters,
    gnn_propagate,
    gnn_ranking_loss,
    gnn_root_scores,
)
from rootkgd.graph import KnowledgeGraph


def test_gnn_propagate_uses_relation_specific_weights() -> None:
    graph = KnowledgeGraph()
    for node in ("a", "b", "c"):
        graph.add_node(node, "variable")
    graph.add_edge("a", "State", "b")
    graph.add_edge("a", "Output", "c")
    params = GnnParameters(
        relation_weights={"State": 0.8, "Output": 0.2},
        self_weight=0.0,
        layers=1,
    )

    scores = gnn_propagate(graph, "a", 1.0, params)

    np.testing.assert_allclose(scores["a"], 1.0)
    np.testing.assert_allclose(scores["b"], 0.8)
    np.testing.assert_allclose(scores["c"], 0.2)


def test_gnn_root_scores_rank_source_matching_contribution_pattern() -> None:
    graph = KnowledgeGraph()
    for node in ("x1", "x2", "x3"):
        graph.add_node(node, "variable")
    graph.add_edge("x1", "State", "x2")
    graph.add_edge("x2", "State", "x3")
    params = GnnParameters(
        relation_weights={"State": 0.5},
        self_weight=0.0,
        layers=2,
    )
    contributions = {"x1": 1.0, "x2": 0.5, "x3": 0.25}

    ranked = gnn_root_scores(graph, contributions, ["x1", "x2", "x3"], params)

    assert ranked[0][0] == "x1"


def test_fit_gnn_parameters_reduces_label_ranking_loss() -> None:
    graph = KnowledgeGraph()
    for node in ("x1", "x2", "x3"):
        graph.add_node(node, "variable")
    graph.add_edge("x1", "Useful", "x2")
    graph.add_edge("x3", "Distractor", "x2")
    base = GnnParameters(
        relation_weights={"Useful": 0.05, "Distractor": 0.8},
        self_weight=0.0,
        layers=1,
    )
    case = GnnTrainingCase(
        name="synthetic",
        contributions={"x1": 0.2, "x2": 1.0, "x3": 0.2},
        positive_nodes=("x1",),
    )

    result = fit_gnn_parameters(
        graph,
        [case],
        ["x1", "x2", "x3"],
        base,
        epochs=2,
        regularization=0.0,
    )

    assert result.final_loss < result.base_loss
    assert gnn_ranking_loss(graph, [case], ["x1", "x2", "x3"], result.params) < gnn_ranking_loss(
        graph, [case], ["x1", "x2", "x3"], base
    )


def test_gnn_ranking_loss_penalizes_each_positive_node() -> None:
    graph = KnowledgeGraph()
    for node in ("x1", "x2", "x3"):
        graph.add_node(node, "variable")
    graph.add_edge("x1", "State", "x3")
    params = GnnParameters(
        relation_weights={"State": 1.0},
        self_weight=0.0,
        layers=1,
    )
    case = GnnTrainingCase(
        name="two-positive-case",
        contributions={"x1": 1.0, "x2": 0.0, "x3": 1.0},
        positive_nodes=("x1", "x2"),
    )

    loss = gnn_ranking_loss(graph, [case], ["x1", "x2", "x3"], params)

    assert loss > 0.0
