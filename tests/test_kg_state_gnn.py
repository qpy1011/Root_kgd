import numpy as np

from rootkgd.graph import KnowledgeGraph
from rootkgd.kg_state_gnn import (
    STATE_NAMES,
    StateKgGnnCase,
    augment_graph_with_state_nodes,
    compute_state_evidence,
    fit_state_kg_gnn_parameters_torch,
    initial_state_kg_gnn_parameters,
    kg_state_gnn_ranking_loss,
    kg_state_gnn_root_scores,
    state_node_name,
)


def test_augment_graph_with_state_nodes_embeds_abnormal_states_in_kg() -> None:
    graph = KnowledgeGraph()
    graph.add_node("x1", "variable")
    graph.add_node("Unit", "device")
    graph.add_edge("Unit", "State", "x1")

    augmented = augment_graph_with_state_nodes(graph, ["x1"])

    assert set(augmented.nodes) >= {"x1", "Unit"}
    assert {state_node_name("x1", state) for state in STATE_NAMES}.issubset(augmented.nodes)
    assert augmented.nodes[state_node_name("x1", "high")].kind == "state"
    assert (
        "x1",
        "Has abnormal state",
        state_node_name("x1", "high"),
    ) in {(triple.head, triple.relation, triple.tail) for triple in augmented.triples}
    assert (
        state_node_name("x1", "high"),
        "State evidence of",
        "x1",
    ) in {(triple.head, triple.relation, triple.tail) for triple in augmented.triples}


def test_compute_state_evidence_captures_direction_and_trend() -> None:
    normal = np.array(
        [
            [-1.0, 1.0],
            [0.0, 0.0],
            [1.0, -1.0],
            [-1.0, 1.0],
            [0.0, 0.0],
            [1.0, -1.0],
        ]
    )
    fault_samples = np.array(
        [
            [0.0, 0.0],
            [1.0, -1.0],
            [2.0, -2.0],
            [3.0, -3.0],
        ]
    )

    evidence = compute_state_evidence(normal, fault_samples, ["x1", "x2"])

    assert evidence[state_node_name("x1", "high")] > evidence[state_node_name("x1", "low")]
    assert evidence[state_node_name("x1", "rise")] > evidence[state_node_name("x1", "fall")]
    assert evidence[state_node_name("x2", "low")] > evidence[state_node_name("x2", "high")]
    assert evidence[state_node_name("x2", "fall")] > evidence[state_node_name("x2", "rise")]
    assert all(0.0 <= value <= 1.0 for value in evidence.values())


def test_state_evidence_guides_root_ranking_without_external_fuzzy_rules() -> None:
    graph = KnowledgeGraph()
    for node in ("root", "distractor", "x1"):
        graph.add_node(node, "variable")
    graph.add_edge("root", "Influence", state_node_name("x1", "high"))
    graph.add_edge(state_node_name("x1", "high"), "State evidence of", "x1")
    graph.add_edge("distractor", "Influence", "x1")

    params = initial_state_kg_gnn_parameters(
        graph,
        relation_weights={"Influence": 0.8, "State evidence of": 0.8},
        layers=2,
        state_gate_strength=1.0,
        state_target_weight=1.0,
    )
    case = StateKgGnnCase(
        name="synthetic",
        contributions={"root": 0.1, "distractor": 0.1, "x1": 1.0},
        state_evidence={state_node_name("x1", "high"): 1.0},
        positive_nodes=("root",),
    )

    ranked = kg_state_gnn_root_scores(
        graph,
        case,
        variable_nodes=["root", "distractor", "x1"],
        params=params,
        candidates=["root", "distractor"],
    )

    assert ranked[0][0] == "root"


def test_torch_state_kg_gnn_training_reduces_ranking_loss_when_torch_available() -> None:
    pytest = __import__("pytest")
    torch = pytest.importorskip("torch")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    graph = KnowledgeGraph()
    for node in ("root", "distractor", "x1"):
        graph.add_node(node, "variable")
    graph.add_edge("root", "Useful", state_node_name("x1", "high"))
    graph.add_edge(state_node_name("x1", "high"), "State evidence of", "x1")
    graph.add_edge("distractor", "Distractor", "x1")
    params = initial_state_kg_gnn_parameters(
        graph,
        relation_weights={"Useful": 0.2, "Distractor": 0.9, "State evidence of": 0.5},
        layers=2,
        state_gate_strength=1.0,
        state_target_weight=1.0,
    )
    case = StateKgGnnCase(
        name="torch-state",
        contributions={"root": 0.1, "distractor": 0.1, "x1": 1.0},
        state_evidence={state_node_name("x1", "high"): 1.0},
        positive_nodes=("root",),
    )

    result = fit_state_kg_gnn_parameters_torch(
        graph,
        [case],
        variable_nodes=["root", "distractor", "x1"],
        params=params,
        epochs=30,
        learning_rate=0.1,
        regularization=0.0,
        device=device,
    )

    assert result.final_loss < result.base_loss
    assert kg_state_gnn_ranking_loss(
        graph,
        [case],
        ["root", "distractor", "x1"],
        result.params,
    ) < kg_state_gnn_ranking_loss(graph, [case], ["root", "distractor", "x1"], params)
