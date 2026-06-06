import numpy as np

from rootkgd.graph import KnowledgeGraph
from rootkgd.rfpa import RfpaParameters, cosine_similarity, rfpa, root_scores


def test_rfpa_attenuates_along_typed_relations() -> None:
    graph = KnowledgeGraph()
    graph.add_node("a", "variable")
    graph.add_node("b", "variable")
    graph.add_edge("a", "State", "b")
    params = RfpaParameters(
        distances={"State": 1.0},
        priorities={"State": 1},
        sigma=0.1,
        max_starts=2,
        min_delta=1e-9,
    )

    scores = rfpa(graph, "a", 1.0, params)

    assert scores["a"] == 1.0
    np.testing.assert_allclose(scores["b"], np.exp(-0.1))


def test_rfpa_receive_loss_uses_current_sender_receive_count() -> None:
    graph = KnowledgeGraph()
    for node in ("a", "b", "c"):
        graph.add_node(node, "variable")
    graph.add_edge("a", "State", "b")
    graph.add_edge("b", "State", "c")
    params = RfpaParameters(
        distances={"State": 1.0},
        priorities={"State": 1},
        sigma=0.1,
        max_starts=2,
        min_delta=1e-9,
    )

    scores = rfpa(graph, "a", 1.0, params)

    np.testing.assert_allclose(scores["b"], np.exp(-0.1))
    np.testing.assert_allclose(scores["c"], np.exp(-0.2) / 2.0)


def test_root_scores_rank_candidate_whose_propagation_matches_contributions() -> None:
    graph = KnowledgeGraph()
    for node in ("x1", "x2", "x3"):
        graph.add_node(node, "variable")
    graph.add_edge("x1", "State", "x2")
    graph.add_edge("x2", "State", "x3")
    params = RfpaParameters(
        distances={"State": 1.0},
        priorities={"State": 1},
        sigma=0.1,
        max_starts=3,
        min_delta=1e-9,
    )
    contributions = {"x1": 1.0, "x2": np.exp(-0.1), "x3": np.exp(-0.2)}

    ranked = root_scores(graph, contributions, ["x1", "x2", "x3"], params)

    assert ranked[0][0] == "x1"
    assert cosine_similarity(np.array([1.0, 0.0]), np.array([0.0, 0.0])) == 0.0
