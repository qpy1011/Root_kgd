# Root-KGD Reproduction Progress

## 2026-06-02

- Created planning files for the Root-KGD reproduction task.
- Initial workspace check found the paper Markdown and `tennessee-eastman-profBraatz-master`.
- Extracted the paper's Root-KGD/RBC/RFPA requirements and TEP experiment targets.
- Verified there is no existing implementation in the workspace and no git repository metadata.
- Wrote failing tests for data loading, RBC, and RFPA, then implemented the core modules.
- `pytest -q` now passes with 6 tests.
- Added TEP graph construction, experiment runner, CLI, outputs, requirements, and reproduction notes.
- Corrected RFPA receive-loss implementation after a failing test showed formula (8) should use the current sender's receive count.
- Final verification: `pytest -q` passed with 12 tests; `python run_reproduction.py` regenerated `outputs/`.
- Added TEP PIKG visualization export support and generated files under `visualizations/tep_pikg`.
- Verification: `pytest -q` passed with 15 tests; exported visualization data contains 79 nodes and 273 edges.
- Added `neo4j_import.cypher` for Neo4j `LOAD CSV` import and regenerated visualization files.
- Verification: `pytest -q` passed with 16 tests; Neo4j CSV export contains 79 nodes and 273 edges.
- Updated Neo4j CSV/Cypher export for Chinese display names: node `name` now imports from `name_zh`, relation `name` imports from `relation_zh`.
- Verification: `pytest -q` passed with 17 tests; regenerated `tep_pikg_nodes.csv`, `tep_pikg_edges.csv`, and `neo4j_import.cypher`.
- Refined the TEP PIKG against the Braatz TE source comments and stream balance equations: corrected Stream 4/5/8/10/11/14 flow paths, added cooling-water and stripper-steam utility entities, added B in Stream 4, and added the D-to-F side-reaction.
- Verification: `pytest -q` passed with 20 tests; `python run_reproduction.py` regenerated `outputs/`, with IDV(1) now ranking `x45` first and Stream 4 first.
- Export note: `visualizations/tep_pikg/tep_pikg_nodes.csv` was locked by another process, so updated visualization files were generated under `visualizations/tep_pikg_updated`.
- Added a lightweight relation-aware GNN extension in `rootkgd/gnn.py` and a `run_gnn_experiment.py` entry point.
- Verification: `python run_gnn_experiment.py` generated `outputs_gnn/`; GNN training loss improved from `0.05477` to `0.02194`, and top variable/physical rankings matched the target nodes for IDV(1), IDV(4), IDV(6), and IDV(12).

## 2026-06-03

- Started elevator-domain KG task under `elevator_KG`.
- Inspected local files: `2025年200台电梯困人工单数据.xlsx` and `fau_rep.xls`.
- First PowerShell here-string attempt failed because the terminator was missing; reran with correct wrapper.
- Directly embedding Chinese file/sheet names in PowerShell-fed Python caused console-encoding replacement with `?`; switched to `Path.glob()` and sheet indexes.
- Installed `xlrd==2.0.2` into `elevator_KG/.deps` to read the legacy `.xls` without changing the global Python environment.
- Profiled local data: rescue-order workbook has 2,177 rows; fault-report workbook has 65,535 rows plus a fault-cause count sheet.
- Added `tests/test_elevator_kg.py` with red-green coverage for classification, domain edges, privacy-preserving work-order export, and Neo4j CSV/Cypher output.
- Added `elevator_KG/elevator_kg_builder.py` and generated `elevator_kg_nodes.csv`, `elevator_kg_edges.csv`, `neo4j_import.cypher`, `elevator_kg.json`, `elevator_kg_summary.json`, `elevator_kg_schema.md`, `elevator_kg_sources.md`, and `README.md`.
- Elevator KG export summary: 3,572 nodes and 20,645 edges. It includes systems/components, fault categories, phenomena, actions, standards/rules, local work orders, elevator assets, organizations, locations, raw fault texts, aggregate report causes, fault locations, and replacement part types.
- Verification: `pytest tests/test_elevator_kg.py -q` passed with 4 tests; `pytest -q` passed with 28 tests.

## 2026-06-07

- Upgraded the GNN from relation-only propagation weights to edge-specific weights.
- Added edge keys in the form `head|relation|tail`, edge-weight propagation, full edge-weight initialization from the TEP graph, focused trainable-edge selection, and hard-negative training candidates.
- Updated `run_gnn_experiment.py` to use two-stage training: relation-level pretraining first, then edge-specific fine-tuning; it now writes `outputs_gnn_edge/edge_weights.csv`.
- A naive all-edge coordinate search with current defaults timed out at 180s and 240s; the two-stage/focused-edge training completed in about 67s.
- Edge-specific GNN output summary: relation loss `0.112113 -> 0.001886`, edge fine-tuning loss `0.025714 -> 0.007335`, 323 exported edge weights, 13 edge weights changed from relation priors.
- Edge-specific GNN top results: IDV(1) `x4`/Stream 4, IDV(4) `x51`/Stream 12, IDV(6) `x1`/Stream 1, IDV(12) `x11`/Stream 14.
- Verification: `pytest -q` passed with 35 tests; `python run_gnn_experiment.py --output-dir outputs_gnn_edge` completed and regenerated GNN outputs.
