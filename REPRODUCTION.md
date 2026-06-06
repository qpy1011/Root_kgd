# Root-KGD Reproduction Notes

This workspace now contains a runnable reproduction of the TEP part of:

`Root-KGD: A Novel Framework for Root Cause Diagnosis Based on Knowledge Graph and Industrial Data`

## Scope

- Implemented: TEP experiments for IDV(1), IDV(4), IDV(6), and IDV(12).
- Implemented: RBC/SPE contribution extraction, PIKG construction from public TEP descriptions, RFPA, RootScore ranking, CSV/JSON export.
- Implemented: a lightweight relation-aware GNN extension that learns PIKG relation propagation weights from labeled TEP cases.
- Not implemented: MFF experiments, because no MFF data is present in the workspace.
- Approximation: the paper does not publish the complete TEP PIKG triple list, so `rootkgd/tep.py` reconstructs a reasonable PIKG from the local TEP README and paper examples.

## Run

```powershell
python run_reproduction.py
```

Run the lightweight GNN-Root-KGD extension:

```powershell
python run_gnn_experiment.py
```

Default inputs:

- data: `tennessee-eastman-profBraatz-master`
- fault cases: `1 4 6 12`
- fault window: samples `160..259`
- PCA principal-component ratio: `0.5`
- output: `outputs`

Custom run:

```powershell
python run_reproduction.py --faults 1 4 6 12 --fault-start 160 --window 100 --r-pc 0.5 --output-dir outputs
```

## Outputs

Each fault case writes:

- `idvXX_rbc_contribution.csv`: averaged normalized RBC contribution over the first 100 fault samples.
- `idvXX_variables.csv`: Root-KGD variable root-cause ranking.
- `idvXX_physical.csv`: Root-KGD stream/device ranking.
- `summary.json`: expected paper targets and reproduced ranks.

The GNN extension writes to `outputs_gnn` by default:

- `idvXX_gnn_variables.csv`: GNN variable root-cause ranking.
- `idvXX_gnn_physical.csv`: GNN stream/device ranking.
- `idvXX_gnn_all.csv`: top all-node ranking.
- `relation_weights.csv`: learned relation propagation weights.
- `summary.json`: GNN loss, learned weights, and target ranks.

## Current Result Summary

| Fault | Paper target | Reproduced variable rank | Reproduced stream/device rank |
|---|---|---|---|
| IDV(1) | `x4` or `x45`, Stream 4 | `x45` rank 1, `x4` rank 6 | Stream 4 rank 1 |
| IDV(4) | `x51`, Stream 12 | `x51` rank 1 | Stream 12 rank 1, Reactor rank 2 |
| IDV(6) | `x1` or `x44`, Stream 1 | `x1` rank 1, `x44` rank 2 | Stream 1 rank 1 |
| IDV(12) | `x11`, Stream 14 | `x11` rank 1 | Stream 14 rank 1, Separator rank 3, Condenser rank 6 |

## GNN Extension Summary

The lightweight GNN keeps RBC and PIKG unchanged, but replaces the fixed RFPA propagation strengths with learned relation-aware message passing. The current run reduces the labeled ranking loss from `0.05477` to `0.02194`.

| Fault | GNN top variable | GNN top stream/device |
|---|---|---|
| IDV(1) | `x45` | Stream 4 |
| IDV(4) | `x51` | Stream 12 |
| IDV(6) | `x1` | Stream 1 |
| IDV(12) | `x11` | Stream 14 |

## Implementation Notes

- `rootkgd/rbc.py` implements SPE-based Reconstruction-Based Contribution using PCA residual projection.
- `rootkgd/rfpa.py` implements RFPA with a priority queue.
- `rootkgd/gnn.py` implements relation-aware GNN propagation and a lightweight relation-weight trainer using NumPy.
- RFPA formula (8) is implemented using the current sender's receive count, matching the paper pseudocode line that increments `N_r[e_v]`.
- `rootkgd/tep.py` contains the reconstructed TEP graph and RFPA parameters from Table 2.
- The TEP graph now models the stripper overhead stream, recycle compressor path, condenser outlet stream, cooling-water utilities, stripper steam, B in stream 4, and the D-to-F side-reaction more explicitly.

## Tests

```powershell
pytest -q
```

Current status: 20 tests pass.
