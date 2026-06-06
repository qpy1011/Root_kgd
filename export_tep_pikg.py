from __future__ import annotations

import argparse
from pathlib import Path

from rootkgd.visualization import export_tep_pikg


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export TEP PIKG visualization files.")
    parser.add_argument(
        "--output-dir",
        default="visualizations/tep_pikg",
        help="Directory for nodes, edges, GraphML, DOT, JSON, and HTML files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    files = export_tep_pikg(Path(args.output_dir))
    for label, path in files.items():
        print(f"{label}: {path.resolve()}")


if __name__ == "__main__":
    main()

