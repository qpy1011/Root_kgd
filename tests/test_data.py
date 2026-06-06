from pathlib import Path

import numpy as np

from rootkgd.data import load_te_dat


def test_load_te_dat_transposes_variable_major_files(tmp_path: Path) -> None:
    source = tmp_path / "d00.dat"
    matrix = np.arange(52 * 3, dtype=float).reshape(52, 3)
    np.savetxt(source, matrix)

    loaded = load_te_dat(source)

    assert loaded.shape == (3, 52)
    np.testing.assert_array_equal(loaded, matrix.T)


def test_load_te_dat_keeps_sample_major_files(tmp_path: Path) -> None:
    source = tmp_path / "d01_te.dat"
    matrix = np.arange(4 * 52, dtype=float).reshape(4, 52)
    np.savetxt(source, matrix)

    loaded = load_te_dat(source)

    assert loaded.shape == (4, 52)
    np.testing.assert_array_equal(loaded, matrix)

