# Root-KGD Reproduction Plan

Goal: Reproduce the paper's Root-KGD framework from the provided Markdown paper using the existing workspace, producing runnable code, data-processing steps, experiments, and verification notes.

## Phases

| Phase | Status | Purpose |
|---|---|---|
| 1. Paper extraction | complete | Read the paper and extract the method, datasets, assumptions, metrics, and required outputs. |
| 2. Repository survey | complete | Inspect existing TE process code/data and identify reusable assets. |
| 3. Reproduction design | complete | Map the paper's Root-KGD pipeline to concrete modules, scripts, and experiment configs. |
| 4. Implementation | complete | Build the reproducible pipeline with scoped code changes. |
| 5. Verification | complete | Run available tests/experiments and compare outputs with paper claims where possible. |
| 6. Delivery notes | complete | Document usage, limitations, and remaining gaps. |
| 7. PIKG visualization files | complete | Export TEP PIKG nodes, edges, GraphML, DOT, and an HTML viewer. |
| 8. Elevator domain KG | complete | Use the new elevator work-order files plus web-researched domain references to build a Neo4j-ready elevator fault knowledge graph. |

## Decisions

| Decision | Rationale |
|---|---|
| Use local planning files | The task is multi-step and will require repeated paper/repo inspection. |
| Treat the paper Markdown as source data | It may contain extraction artifacts, so claims must be cross-checked inside the file before implementation. |
| Reconstruct TEP PIKG from public descriptions | The full PIKG triples are not published; the reproduction uses an auditable approximation in `rootkgd/tep.py`. |
| Build elevator KG inside `elevator_KG` | Keep elevator-domain artifacts isolated from the TEP implementation while reusing the project’s CSV/Cypher export style. |
| Preserve privacy in elevator KG export | Export work-order ids, equipment ids, organizations, places, fault texts, categories, counts, and times, but omit names and phone numbers. |

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|
