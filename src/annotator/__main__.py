"""
__main__.py

CLI entry point: python -m annotator
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from .annotate import annotate, check_optimizer_disabled


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Annotate solc standard JSON output with ethdebug format data.\n"
            "\n"
            "The compilation must have been performed with the optimizer disabled.\n"
            "For full annotation, request the following output fields:\n"
            "  ast, metadata, storageLayout,\n"
            "  evm.bytecode.object, evm.bytecode.sourceMap,\n"
            "  evm.deployedBytecode.object, evm.deployedBytecode.sourceMap"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "output_file",
        nargs="?",
        default="-",
        help="Path to solc standard JSON output file, or '-' for stdin (default: stdin)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Annotated output file path (default: stdout)",
    )
    parser.add_argument(
        "-i",
        "--input-json",
        dest="input_json",
        help=(
            "Path to the original solc standard JSON *input* file. "
            "Used to include source file contents in the ethdebug Info object."
        ),
    )
    parser.add_argument(
        "-s",
        "--sources-dir",
        dest="sources_dirs",
        action="append",
        default=[],
        metavar="DIR",
        help=(
            "Directory to search for source files (can be repeated). "
            "Used to include source file contents when --input-json is not provided."
        ),
    )
    args = parser.parse_args()

    if args.output_file == "-":
        solc_output = json.load(sys.stdin)
    else:
        with open(args.output_file) as f:
            solc_output = json.load(f)

    input_json: Optional[dict] = None
    if args.input_json:
        with open(args.input_json) as f:
            input_json = json.load(f)

    check_optimizer_disabled(solc_output)
    annotated = annotate(
        solc_output,
        source_dirs=args.sources_dirs or None,
        input_json=input_json,
    )

    text = json.dumps(annotated, indent=2)
    if args.output:
        with open(args.output, "w") as f:
            f.write(text)
    else:
        print(text)


if __name__ == "__main__":
    main()
