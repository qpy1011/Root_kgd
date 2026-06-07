import numpy as np

import run_gnn_experiment
from rootkgd.gnn import (
    GnnParameters,
    GnnTrainingCase,
    edge_key,
    fit_gnn_parameters,
    fit_gnn_parameters_torch,
    gnn_propagate,
    gnn_ranking_loss,
    gnn_root_scores,
    initial_gnn_parameters_from_rfpa,
    trainable_edge_keys,
    training_candidate_nodes,
    with_edge_weights_from_graph,
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


def test_gnn_propagate_prefers_edge_specific_weights() -> None:
    graph = KnowledgeGraph()
    for node in ("a", "b", "c"):
        graph.add_node(node, "variable")
    graph.add_edge("a", "State", "b")
    graph.add_edge("a", "State", "c")
    params = GnnParameters(
        relation_weights={"State": 0.5},
        edge_weights={
            edge_key("a", "State", "b"): 0.9,
            edge_key("a", "State", "c"): 0.1,
        },
        self_weight=0.0,
        layers=1,
    )

    scores = gnn_propagate(graph, "a", 1.0, params)

    np.testing.assert_allclose(scores["b"], 0.9)
    np.testing.assert_allclose(scores["c"], 0.1)


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


def test_initial_gnn_parameters_can_assign_every_edge_weight() -> None:
    graph = KnowledgeGraph()
    for node in ("a", "b", "c"):
        graph.add_node(node, "variable")
    graph.add_edge("a", "State", "b")
    graph.add_edge("a", "State", "c")

    params = initial_gnn_parameters_from_rfpa(
        {"State"},
        {"State": 1.0},
        sigma=0.1,
        layers=1,
        graph=graph,
    )

    assert set(params.edge_weights) == {
        edge_key("a", "State", "b"),
        edge_key("a", "State", "c"),
    }
    np.testing.assert_allclose(params.edge_weights[edge_key("a", "State", "b")], np.exp(-0.1))


def test_with_edge_weights_from_graph_expands_relation_weights_to_each_edge() -> None:
    graph = KnowledgeGraph()
    for node in ("a", "b", "c"):
        graph.add_node(node, "variable")
    graph.add_edge("a", "State", "b")
    graph.add_edge("a", "Output", "c")
    relation_params = GnnParameters(
        relation_weights={"State": 0.8, "Output": 0.2},
        self_weight=0.0,
        layers=1,
    )

    edge_params = with_edge_weights_from_graph(graph, relation_params)

    assert edge_params.edge_weights == {
        edge_key("a", "State", "b"): 0.8,
        edge_key("a", "Output", "c"): 0.2,
    }


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


def test_fit_gnn_parameters_can_adjust_one_edge_without_changing_same_relation_edge() -> None:
    graph = KnowledgeGraph()
    for node in ("root", "useful", "noise"):
        graph.add_node(node, "variable")
    graph.add_edge("root", "State", "useful")
    graph.add_edge("root", "State", "noise")
    base = GnnParameters(
        relation_weights={"State": 0.5},
        edge_weights={
            edge_key("root", "State", "useful"): 0.05,
            edge_key("root", "State", "noise"): 0.8,
        },
        self_weight=0.0,
        layers=1,
    )
    case = GnnTrainingCase(
        name="edge-specific",
        contributions={"root": 0.2, "useful": 1.0, "noise": 0.0},
        positive_nodes=("root",),
    )

    result = fit_gnn_parameters(
        graph,
        [case],
        ["root", "useful", "noise"],
        base,
        epochs=2,
        regularization=0.0,
    )

    useful_key = edge_key("root", "State", "useful")
    noise_key = edge_key("root", "State", "noise")
    assert result.final_loss < result.base_loss
    assert result.params.edge_weights[useful_key] > base.edge_weights[useful_key]
    assert result.params.edge_weights[noise_key] <= base.edge_weights[noise_key]


def test_trainable_edge_keys_focus_on_positive_and_high_contribution_neighborhoods() -> None:
    graph = KnowledgeGraph()
    for node in ("root", "useful", "noise", "far"):
        graph.add_node(node, "variable")
    graph.add_edge("root", "State", "useful")
    graph.add_edge("noise", "State", "far")
    case = GnnTrainingCase(
        name="focused",
        contributions={"root": 0.2, "useful": 1.0, "noise": 0.0, "far": 0.0},
        positive_nodes=("root",),
    )

    keys = trainable_edge_keys(graph, [case], ["root", "useful", "noise", "far"], hops=1, top_contribution_nodes=1)

    assert edge_key("root", "State", "useful") in keys
    assert edge_key("noise", "State", "far") not in keys


def test_training_candidate_nodes_keep_positives_and_hard_negatives() -> None:
    graph = KnowledgeGraph()
    for node in ("root", "useful", "hard_negative", "low"):
        graph.add_node(node, "variable")
    graph.add_edge("hard_negative", "State", "useful")
    params = GnnParameters(relation_weights={"State": 1.0}, self_weight=0.0, layers=1)
    case = GnnTrainingCase(
        name="candidates",
        contributions={"root": 0.2, "useful": 1.0, "hard_negative": 0.1, "low": 0.0},
        positive_nodes=("root",),
    )

    candidates = training_candidate_nodes(
        graph,
        [case],
        ["root", "useful", "hard_negative", "low"],
        params,
        top_contribution_nodes=1,
        hard_negatives_per_case=2,
    )

    assert "root" in candidates
    assert "useful" in candidates
    assert "hard_negative" in candidates


def test_run_gnn_experiment_exports_edge_weights(tmp_path) -> None:
    weights = {
        edge_key("a", "State", "b"): 0.9,
        edge_key("a", "State", "c"): 0.1,
    }

    output = tmp_path / "edge_weights.csv"
    run_gnn_experiment._write_edge_weights(output, weights)

    content = output.read_text(encoding="utf-8")
    assert "head,relation,tail,edge_key,weight" in content
    assert "a,State,b,a|State|b,0.9" in content
    assert "a,State,c,a|State|c,0.1" in content


def test_run_gnn_experiment_evaluation_metrics_count_best_target_ranks() -> None:
    cases = [
        {
            "expected_variable_ranks": {"x1": 1, "x2": 3},
            "expected_physical_ranks": {"Stream 1": 2},
        },
        {
            "expected_variable_ranks": {"x3": 4},
            "expected_physical_ranks": {"Stream 2": None},
        },
    ]

    metrics = run_gnn_experiment._evaluation_metrics(cases)

    assert metrics["case_count"] == 2
    assert metrics["variable_top1"] == 1
    assert metrics["variable_top3"] == 1
    assert metrics["physical_top1"] == 0
    assert metrics["physical_top3"] == 1


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


def test_torch_fit_matches_basic_ranking_behavior_when_torch_available() -> None:
    pytest = __import__("pytest")
    torch = pytest.importorskip("torch")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    graph = KnowledgeGraph()
    for node in ("x1", "x2", "x3"):
        graph.add_node(node, "variable")
    graph.add_edge("x1", "Useful", "x2")
    graph.add_edge("x3", "Distractor", "x2")
    base = GnnParameters(
        relation_weights={"Useful": 0.2, "Distractor": 0.8},
        edge_weights={
            edge_key("x1", "Useful", "x2"): 0.2,
            edge_key("x3", "Distractor", "x2"): 0.8,
        },
        self_weight=0.0,
        layers=1,
    )
    case = GnnTrainingCase(
        name="torch-synthetic",
        contributions={"x1": 0.2, "x2": 1.0, "x3": 0.2},
        positive_nodes=("x1",),
    )

    result = fit_gnn_parameters_torch(
        graph,
        [case],
        ["x1", "x2", "x3"],
        base,
        epochs=20,
        learning_rate=0.1,
        regularization=0.0,
        device=device,
    )

    assert result.final_loss < result.base_loss
    assert result.params.edge_weights[edge_key("x1", "Useful", "x2")] > base.edge_weights[edge_key("x1", "Useful", "x2")]
