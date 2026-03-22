"""
annotate.py

Core annotation logic: validates optimizer settings and annotates
solc standard JSON output with ethdebug data.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Optional

from .ast_walker import _ASTWalker, _src_to_range
from .program import _get_compiler_version, build_program
from .variables import build_storage_map


def check_optimizer_disabled(solc_output: dict) -> None:
    """Raise RuntimeError if any contract's metadata shows optimizer enabled."""
    for filename, contracts in solc_output.get("contracts", {}).items():
        for contract_name, contract_data in contracts.items():
            metadata_str = contract_data.get("metadata")
            if not metadata_str:
                continue
            try:
                metadata = json.loads(metadata_str)
            except json.JSONDecodeError:
                continue
            optimizer = metadata.get("settings", {}).get("optimizer", {})
            if optimizer.get("enabled", False):
                raise RuntimeError(
                    f"Optimizer is enabled for {filename}:{contract_name}. "
                    "ethdebug annotation requires compilation with optimizer disabled."
                )


def _read_source_content(
    path: str,
    source_dirs: Optional[list[str]] = None,
    input_json: Optional[dict] = None,
) -> Optional[str]:
    """Try to resolve source file contents from disk or from the original input JSON."""
    # Try the original solc input JSON first (fastest, no I/O)
    if input_json:
        src_entry = input_json.get("sources", {}).get(path)
        if src_entry and isinstance(src_entry.get("content"), str):
            return src_entry["content"]

    # Try to read from disk
    search_dirs: list[str] = ["."]
    if source_dirs:
        search_dirs = source_dirs + search_dirs

    for base in search_dirs:
        candidate = os.path.join(base, path)
        if os.path.isfile(candidate):
            try:
                with open(candidate, encoding="utf-8") as f:
                    return f.read()
            except OSError:
                pass

    return None


def annotate(
    solc_output: dict,
    source_dirs: Optional[list[str]] = None,
    input_json: Optional[dict] = None,
) -> dict:
    """Annotate a solc standard JSON output dict with ethdebug data in-place."""

    # Source ID map: AST file_id (int) → ethdebug source id (same int for solc)
    source_id_map: dict[int, int] = {}
    sources_list: list[dict] = []

    for path, src_data in solc_output.get("sources", {}).items():
        fid = src_data.get("id", 0)
        source_id_map[fid] = fid
        contents = _read_source_content(path, source_dirs, input_json)
        src_entry: dict = {"id": fid, "path": path, "language": "Solidity"}
        if contents is not None:
            src_entry["contents"] = contents
        sources_list.append(src_entry)

    # Walk all ASTs to collect variables, structs, enums
    walker = _ASTWalker()
    for src_data in solc_output.get("sources", {}).values():
        ast = src_data.get("ast")
        if ast:
            walker.walk(ast)

    # Compilation ID (deterministic hash of the output)
    comp_hash = hashlib.sha256(
        json.dumps(solc_output, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    compilation_id = f"__{comp_hash}"

    compiler_version = _get_compiler_version(solc_output)

    # Contract source ranges: contract_name → ethdebug source range
    contract_definitions: dict[str, dict] = {}
    for src_data in solc_output.get("sources", {}).values():
        ast = src_data.get("ast")
        if not ast:
            continue
        for node in ast.get("nodes", []):
            if node.get("nodeType") == "ContractDefinition":
                cname = node.get("name")
                src = _src_to_range(node.get("src"))
                if src:
                    sid = source_id_map.get(src["file_id"], src["file_id"])
                    contract_definitions[cname] = {
                        "source": {"id": sid},
                        "range": {"offset": src["offset"], "length": src["length"]},
                    }

    programs: list[dict] = []

    for filename, contracts in solc_output.get("contracts", {}).items():
        for contract_name, contract_data in contracts.items():
            storage_map: Optional[dict] = None
            sl = contract_data.get("storageLayout")
            if sl:
                storage_map = build_storage_map(sl)

            state_vars = walker.contract_state_vars.get(contract_name, [])
            contract_def = contract_definitions.get(contract_name)

            evm = contract_data.get("evm", {})

            # Creation bytecode
            bytecode_obj = evm.get("bytecode", {})
            bytecode_hex = bytecode_obj.get("object", "")
            if bytecode_hex and bytecode_hex != "0x":
                prog = build_program(
                    contract_name=contract_name,
                    contract_definition=contract_def,
                    environment="create",
                    bytecode_hex=bytecode_hex,
                    source_map_str=bytecode_obj.get("sourceMap", ""),
                    state_vars=state_vars,
                    storage_map=storage_map,
                    source_id_map=source_id_map,
                    walker=walker,
                )
                programs.append(prog)
                solc_output["contracts"][filename][contract_name]["evm"]["bytecode"][
                    "ethdebug"
                ] = prog

            # Deployed bytecode
            deployed_obj = evm.get("deployedBytecode", {})
            deployed_hex = deployed_obj.get("object", "")
            if deployed_hex and deployed_hex != "0x":
                deployed_prog = build_program(
                    contract_name=contract_name,
                    contract_definition=contract_def,
                    environment="call",
                    bytecode_hex=deployed_hex,
                    source_map_str=deployed_obj.get("sourceMap", ""),
                    state_vars=state_vars,
                    storage_map=storage_map,
                    source_id_map=source_id_map,
                    walker=walker,
                )
                programs.append(deployed_prog)
                solc_output["contracts"][filename][contract_name]["evm"]["deployedBytecode"][
                    "ethdebug"
                ] = deployed_prog

    # Top-level ethdebug Info object
    solc_output["ethdebug"] = {
        "compilation": {
            "id": compilation_id,
            "compiler": {"name": "solc", "version": compiler_version},
            "sources": sources_list,
        },
        "programs": programs,
    }

    return solc_output
