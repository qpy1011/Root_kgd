import numpy as np

from rootkgd.rbc import fit_rbc_model, mean_fault_contribution, spe_rbc


def test_spe_rbc_returns_nonnegative_variable_contributions() -> None:
    normal = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 1.0, 0.2],
            [2.0, 2.1, 0.1],
            [3.0, 3.0, 0.3],
            [4.0, 4.1, 0.2],
        ]
    )
    model = fit_rbc_model(normal, principal_component_ratio=0.7)

    contribution = spe_rbc(np.array([4.0, 4.0, 6.0]), model)

    assert contribution.shape == (3,)
    assert np.all(contribution >= 0.0)
    assert contribution[2] == contribution.max()


def test_mean_fault_contribution_normalizes_each_sample_before_average() -> None:
    normal = np.array(
        [
            [0.0, 0.0],
            [1.0, 1.0],
            [2.0, 2.0],
            [3.0, 3.0],
            [4.0, 4.0],
        ]
    )
    model = fit_rbc_model(normal, principal_component_ratio=0.5)
    fault = np.array([[10.0, 0.0], [0.0, 20.0]])

    contribution = mean_fault_contribution(fault, model)

    assert contribution.shape == (2,)
    np.testing.assert_allclose(contribution.sum(), 1.0)
    assert np.all(contribution >= 0.0)

