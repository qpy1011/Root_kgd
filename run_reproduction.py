from __future__ import annotations

import argparse
from pathlib import Path

from rootkgd.experiment import paper_targets, run_tep_reproduction


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the TEP Root-KGD reproduction.")
    parser.add_argument(
        "--data-dir",
        default="tennessee-eastman-profBraatz-master",
        help="Directory containing d00.dat and dXX_te.dat files.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory for CSV and JSON reproduction outputs.",
    )
    parser.add_argument(
        "--faults",
        nargs="+",
        type=int,
        default=[1, 4, 6, 12],
        help="TEP IDV fault numbers to run.",
    )
    parser.add_argument("--fault-start", type=int, default=160)
    parser.add_argument("--window", type=int, default=100)
    parser.add_argument("--r-pc", type=float, default=0.56)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = run_tep_reproduction(
        data_dir=Path(args.data_dir),
        fault_ids=args.faults,
        output_dir=Path(args.output_dir),
        fault_start=args.fault_start,
        window=args.window,
        principal_component_ratio=args.r_pc,
    )
    targets = paper_targets()
    for result in results:
        target = targets.get(result.fault_id)
        expected = ", ".join(target.root_variables) if target else "n/a"
        top_variable = result.variable_rank[0] if result.variable_rank else ("n/a", 0.0)
        top_physical = result.physical_rank[0] if result.physical_rank else ("n/a", 0.0)
        print(
            f"IDV({result.fault_id}) expected [{expected}] | "
            f"top variable {top_variable[0]}={top_variable[1]:.5f} | "
            f"top physical {top_physical[0]}={top_physical[1]:.5f}"
        )
    print(f"Wrote outputs to {Path(args.output_dir).resolve()}")


if __name__ == "__main__":
    main()

