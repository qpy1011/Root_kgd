import numpy as np

import run_kg_state_gnn_experiment
from rootkgd.kg_state_gnn import STATE_BACK_RELATION, STATE_RELATION


def test_initial_relation_weights_include_state_kg_relations() -> None:
    weights = run_kg_state_gnn_experiment._initial_relation_weights(
        relations={"State", STATE_RELATION, STATE_BACK_RELATION},
        rfpa_distances={"State": 1.0},
        sigma=0.1,
    )

    np.testing.assert_allclose(weights["State"], np.exp(-0.1))
    assert weights[STATE_RELATION] > weights["State"]
    assert weights[STATE_BACK_RELATION] > weights["State"]


def test_evaluation_metrics_count_best_expected_ranks() -> None:
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

    metrics = run_kg_state_gnn_experiment._evaluation_metrics(cases)

    assert metrics == {
        "case_count": 2,
        "variable_top1": 1,
        "variable_top3": 1,
        "physical_top1": 0,
        "physical_top3": 1,
    }
