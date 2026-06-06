from __future__ import annotations

from dataclasses import dataclass

import numpy as np


EPSILON = 1e-12


@dataclass(frozen=True)
class RbcModel:
    mean: np.ndarray
    scale: np.ndarray
    components: np.ndarray
    residual_projection: np.ndarray
    n_components: int
    eigenvalues: np.ndarray


def fit_rbc_model(data: np.ndarray, principal_component_ratio: float = 0.5) -> RbcModel:
    if not 0.0 < principal_component_ratio <= 1.0:
        raise ValueError("principal_component_ratio must be in (0, 1]")
    if data.ndim != 2:
        raise ValueError(f"Expected 2-D training data, got {data.shape}")

    mean = data.mean(axis=0)
    scale = data.std(axis=0, ddof=1)
    scale = np.where(scale < EPSILON, 1.0, scale)
    standardized = (data - mean) / scale
    covariance = standardized.T @ standardized / max(1, standardized.shape[0] - 1)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]

    positive_total = np.maximum(eigenvalues, 0.0).sum()
    if positive_total <= EPSILON:
        n_components = 1
    else:
        cumulative = np.cumsum(np.maximum(eigenvalues, 0.0)) / positive_total
        n_components = int(np.searchsorted(cumulative, principal_component_ratio) + 1)
    n_components = min(max(1, n_components), data.shape[1] - 1)

    components = eigenvectors[:, :n_components]
    residual_projection = np.eye(data.shape[1]) - components @ components.T
    return RbcModel(
        mean=mean,
        scale=scale,
        components=components,
        residual_projection=residual_projection,
        n_components=n_components,
        eigenvalues=eigenvalues,
    )


def spe_rbc(sample: np.ndarray, model: RbcModel) -> np.ndarray:
    z = (np.asarray(sample, dtype=float) - model.mean) / model.scale
    residual = model.residual_projection @ z
    diagonal = np.diag(model.residual_projection)
    diagonal = np.where(np.abs(diagonal) < EPSILON, EPSILON, diagonal)
    contribution = (residual**2) / diagonal
    return np.maximum(contribution, 0.0)


def normalize_contribution(contribution: np.ndarray) -> np.ndarray:
    contribution = np.maximum(np.asarray(contribution, dtype=float), 0.0)
    total = contribution.sum()
    if total <= EPSILON:
        return np.full_like(contribution, 1.0 / contribution.size)
    return contribution / total


def mean_fault_contribution(samples: np.ndarray, model: RbcModel) -> np.ndarray:
    if samples.ndim == 1:
        samples = samples.reshape(1, -1)
    rows = [normalize_contribution(spe_rbc(sample, model)) for sample in samples]
    return normalize_contribution(np.mean(rows, axis=0))

