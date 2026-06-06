from __future__ import annotations

from pathlib import Path

import numpy as np


TEP_VARIABLE_COUNT = 52


def load_te_dat(path: str | Path) -> np.ndarray:
    """Load a Tennessee Eastman `.dat` file as samples x variables."""
    data = np.loadtxt(Path(path), dtype=float)
    if data.ndim != 2:
        raise ValueError(f"Expected a 2-D matrix in {path!s}, got shape {data.shape}")
    if data.shape[1] == TEP_VARIABLE_COUNT:
        return data
    if data.shape[0] == TEP_VARIABLE_COUNT:
        return data.T
    raise ValueError(
        f"Cannot infer TE orientation for {path!s}: expected one dimension to be "
        f"{TEP_VARIABLE_COUNT}, got {data.shape}"
    )


def load_tep_fault(data_dir: str | Path, fault_id: int, testing: bool = True) -> np.ndarray:
    suffix = "_te" if testing else ""
    return load_te_dat(Path(data_dir) / f"d{fault_id:02d}{suffix}.dat")


def load_tep_normal(data_dir: str | Path, testing: bool = False) -> np.ndarray:
    suffix = "_te" if testing else ""
    return load_te_dat(Path(data_dir) / f"d00{suffix}.dat")

