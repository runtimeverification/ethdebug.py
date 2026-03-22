"""
program.py

Builds ethdebug Program objects from bytecode and source maps.
"""

from __future__ import annotations

import json
from typing import Optional

from .ast_walker import _ASTWalker
from .bytecode import decode_bytecode, decode_source_map
from .variables import build_variable_entry


def _range_contains(outer: dict, inner: dict) -> bool:
    """True if outer source range fully contains inner."""
    if outer.get("file_id") != inner.get("file_id"):
        return False
    o_start = outer["offset"]
    o_end = o_start + outer["length"]
    i_start = inner["offset"]
    i_end = i_start + inner["length"]
    return o_start <= i_start and i_end <= o_end


def _find_function_vars_for_instr(
    instr_src: dict,
    walker: _ASTWalker,
) -> list[dict]:
    """Return all function-level variables whose function body contains instr_src."""
    result = []
    for (fid, foffset, flength), fvars in walker.function_vars.items():
        func_range = {"file_id": fid, "offset": foffset, "length": flength}
        if _range_contains(func_range, instr_src):
            result.extend(fvars)
            break
    return result


def _get_compiler_version(solc_output: dict) -> str:
    for contracts in solc_output.get("contracts", {}).values():
        for contract_data in contracts.values():
            metadata_str = contract_data.get("metadata")
            if metadata_str:
                try:
                    meta = json.loads(metadata_str)
                    v = meta.get("compiler", {}).get("version")
                    if v:
                        return v
                except json.JSONDecodeError:
                    pass
    return solc_output.get("version", "unknown")


def build_program(
    contract_name: str,
    contract_definition: Optional[dict],
    environment: str,
    bytecode_hex: str,
    source_map_str: str,
    state_vars: list[dict],
    storage_map: Optional[dict[str, dict]],
    source_id_map: dict[int, int],
    walker: _ASTWalker,
) -> dict:
    """Build one ethdebug Program object."""

    raw_instrs = decode_bytecode(bytecode_hex)
    smap = decode_source_map(source_map_str) if source_map_str else []

    # --- Initial context: state variables always in scope ---
    initial_vars = []
    for v in state_vars:
        entry = build_variable_entry(v, storage_map, source_id_map, walker)
        if entry:
            initial_vars.append(entry)

    # --- Build instructions ---
    instructions = []
    for i, raw in enumerate(raw_instrs):
        instr: dict = {"offset": raw["offset"]}

        op: dict = {"mnemonic": raw["mnemonic"]}
        if raw["arguments"]:
            op["arguments"] = raw["arguments"]
        instr["operation"] = op

        ctx: dict = {}

        # Source range from source map
        if i < len(smap):
            sm = smap[i]
            s, l, f = sm.get("s", -1), sm.get("l", -1), sm.get("f", -1)
            if s >= 0 and l >= 0 and f >= 0:
                sid = source_id_map.get(f, f)
                ctx["code"] = {
                    "source": {"id": sid},
                    "range": {"offset": s, "length": l},
                }

                # Add function-level variables in scope at this instruction
                instr_src = {"file_id": f, "offset": s, "length": l}
                func_vars_here = _find_function_vars_for_instr(instr_src, walker)
                if func_vars_here:
                    var_entries = []
                    for fv in func_vars_here:
                        entry = build_variable_entry(fv, None, source_id_map, walker)
                        if entry:
                            var_entries.append(entry)
                    if var_entries:
                        ctx["variables"] = var_entries

        if ctx:
            instr["context"] = ctx

        instructions.append(instr)

    # --- Assemble program ---
    program: dict = {
        "environment": environment,
        "instructions": instructions,
    }

    if contract_definition:
        program["contract"] = {
            "name": contract_name,
            "definition": contract_definition,
        }
    else:
        program["contract"] = {"name": contract_name, "definition": {}}

    if initial_vars:
        program["context"] = {"variables": initial_vars}

    return program
