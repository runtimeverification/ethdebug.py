"""
conftest.py

Pytest fixtures shared across the test suite.

The ``compile_solidity`` fixture compiles a Solidity snippet and returns an
:class:`ethdebug_dsl.AnnotatedResult` ready for DSL-based assertions.

Pass ``--generate-docs`` on the pytest command line to emit one Markdown file
per test under ``docs/examples/``.  A file is only generated when the total
instruction count across all programs is at most ``--docs-max-instructions``
(default 200), keeping generated examples small and readable.
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import textwrap
from pathlib import Path
from typing import Optional, cast

import pytest

# ---------------------------------------------------------------------------
# pytest CLI options
# ---------------------------------------------------------------------------

def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--generate-docs",
        action="store_true",
        default=False,
        help="Generate Markdown examples under docs/examples/ for qualifying tests.",
    )
    parser.addoption(
        "--docs-max-instructions",
        type=int,
        default=200,
        metavar="N",
        help="Maximum total instruction count across all programs for a test to "
             "have docs generated (default: 200).",
    )


# ---------------------------------------------------------------------------
# Locate the solc binary
# ---------------------------------------------------------------------------

def _find_solc() -> Optional[str]:
    """Return the path to the best available solc binary, or None."""
    # 1. solc-select managed installs (newest version first)
    artifacts_dir = Path.home() / ".solc-select" / "artifacts"
    if artifacts_dir.exists():
        candidates = sorted(
            (p for p in artifacts_dir.glob("solc-*/solc-*") if p.is_file()),
            key=lambda p: p.name,
            reverse=True,
        )
        for c in candidates:
            if os.access(c, os.X_OK):
                return str(c)

    # 2. PATH
    return shutil.which("solc")


_SOLC_PATH: Optional[str] = _find_solc()


# ---------------------------------------------------------------------------
# Helper: add standard Solidity boilerplate if missing
# ---------------------------------------------------------------------------

_DEFAULT_PRAGMA = "pragma solidity ^0.8.28;"

def _prepare_source(source: str, pragma: Optional[str] = None) -> str:
    source = textwrap.dedent(source).strip()
    if "pragma solidity" not in source:
        header = f"// SPDX-License-Identifier: MIT\n{pragma or _DEFAULT_PRAGMA}"
        source = f"{header}\n\n{source}"
    return source


# ---------------------------------------------------------------------------
# Helper: build solc standard-JSON input
# ---------------------------------------------------------------------------

def _build_input_json(source: str, filename: str = "test.sol") -> dict:
    return {
        "language": "Solidity",
        "sources": {filename: {"content": source}},
        "settings": {
            "optimizer": {"enabled": False},
            "outputSelection": {
                "*": {
                    "": ["ast"],
                    "*": [
                        "metadata",
                        "storageLayout",
                        "evm.bytecode.object",
                        "evm.bytecode.sourceMap",
                        "evm.deployedBytecode.object",
                        "evm.deployedBytecode.sourceMap",
                    ],
                }
            },
        },
    }


# ---------------------------------------------------------------------------
# Helper: invoke solc and annotate
# ---------------------------------------------------------------------------

def _compile_and_annotate(
    source: str,
    pragma: Optional[str] = None,
    filename: str = "test.sol",
) -> "ethdebug_dsl.AnnotatedResult":
    """Compile *source* with solc and annotate with ethdebug data."""
    from tests.ethdebug_dsl import AnnotatedResult
    from annotator import annotate, check_optimizer_disabled

    prepared = _prepare_source(source, pragma)
    input_json = _build_input_json(prepared, filename)

    result = subprocess.run(
        [_SOLC_PATH, "--standard-json"],
        input=json.dumps(input_json).encode(),
        capture_output=True,
        timeout=30,
    )

    output = json.loads(result.stdout)

    errors = [e for e in output.get("errors", []) if e.get("severity") == "error"]
    if errors:
        messages = "\n".join(e.get("formattedMessage", e.get("message", "")) for e in errors)
        raise RuntimeError(f"solc compilation failed:\n{messages}")

    check_optimizer_disabled(output)
    annotated = annotate(output, input_json=input_json)

    return AnnotatedResult(annotated)


# ---------------------------------------------------------------------------
# Doc generation helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent


def _total_instruction_count(annotated: dict) -> int:
    return sum(
        len(prog.get("instructions", []))
        for prog in annotated.get("ethdebug", {}).get("programs", [])
    )


def _ethdebug_for_docs(annotated: dict) -> dict:
    """Return a copy of the ethdebug section with instructions stripped out.

    The full instruction list can be hundreds of entries; for documentation
    purposes we keep the program metadata and initial context but omit the
    per-instruction detail.
    """
    ethdebug = copy.deepcopy(annotated.get("ethdebug", {}))
    for prog in ethdebug.get("programs", []):
        count = len(prog.pop("instructions", []))
        prog["instructions_count"] = count  # leave a breadcrumb
    return ethdebug


def _write_doc(
    test_name: str,
    test_doc: Optional[str],
    source: str,
    annotated: dict,
    docs_dir: Path,
) -> None:
    """Write a Markdown file for *test_name* into *docs_dir*."""
    docs_dir.mkdir(parents=True, exist_ok=True)

    ethdebug = _ethdebug_for_docs(annotated)
    ethdebug_json = json.dumps(ethdebug, indent=2)

    lines: list[str] = []
    lines.append(f"# `{test_name}`\n")

    if test_doc:
        lines.append(textwrap.dedent(test_doc).strip())
        lines.append("\n")

    lines.append("## Solidity source\n")
    lines.append("```solidity")
    lines.append(source)
    lines.append("```\n")

    lines.append("## ethdebug output\n")
    lines.append("```json")
    lines.append(ethdebug_json)
    lines.append("```\n")

    out_path = docs_dir / f"{test_name}.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def compile_solidity(request: pytest.FixtureRequest):
    """Function-scoped factory fixture.

    Returns a callable ``compile(source, *, pragma=None, filename="test.sol")``
    that compiles the given Solidity source and returns an
    :class:`ethdebug_dsl.AnnotatedResult`.

    When ``--generate-docs`` is passed on the command line, the first call to
    the returned factory also writes a Markdown example to ``docs/examples/``
    (provided the total instruction count stays within the configured limit).

    Skips the test if no solc binary can be found.
    """
    if _SOLC_PATH is None:
        pytest.skip("solc binary not found; install via solc-select or PATH")

    generate_docs = bool(cast(bool, request.config.getoption("--generate-docs")))
    max_instructions = int(cast(int, request.config.getoption("--docs-max-instructions")))
    test_name: str = request.node.name
    test_doc: Optional[str] = request.node.function.__doc__

    def _compile(
        source: str,
        *,
        pragma: Optional[str] = None,
        filename: str = "test.sol",
    ) -> "ethdebug_dsl.AnnotatedResult":
        result = _compile_and_annotate(source, pragma=pragma, filename=filename)

        if generate_docs:
            total = _total_instruction_count(result.raw)
            if total <= max_instructions:
                prepared = _prepare_source(source, pragma)
                docs_dir = _REPO_ROOT / "docs" / "examples"
                _write_doc(test_name, test_doc, prepared, result.raw, docs_dir)

        return result

    return _compile
