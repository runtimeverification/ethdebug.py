"""
variables.py

Storage layout parsing and ethdebug variable entry construction.
"""

from __future__ import annotations

from typing import Optional

from .ast_walker import _ASTWalker


def build_storage_map(storage_layout: dict) -> dict[str, dict]:
    """Return {label: {slot, offset}} from solc storageLayout output."""
    result: dict[str, dict] = {}
    for entry in storage_layout.get("storage", []):
        label = entry.get("label")
        if label:
            result[label] = {
                "slot": int(entry.get("slot", "0")),
                "offset": int(entry.get("offset", 0)),
            }
    return result


def _make_source_range(src: Optional[dict], source_id_map: dict[int, int]) -> Optional[dict]:
    if not src:
        return None
    file_id = src.get("file_id", -1)
    source_id = source_id_map.get(file_id, file_id)
    return {
        "source": {"id": source_id},
        "range": {"offset": src["offset"], "length": src["length"]},
    }


def build_variable_entry(
    var: dict,
    storage_map: Optional[dict[str, dict]],
    source_id_map: dict[int, int],
    walker: Optional[_ASTWalker] = None,
) -> Optional[dict]:
    """Build a single ethdebug variable entry dict."""
    entry: dict = {}

    name = var.get("name") or ""
    if name:
        entry["identifier"] = name

    decl = _make_source_range(var.get("src"), source_id_map)
    if decl:
        entry["declaration"] = decl

    typ = var.get("type")

    # Resolve struct members and enum values from walker when available
    if walker and typ:
        raw_type_str = var.get("type_str", "")
        if typ.get("kind") == "struct" and not typ.get("contains"):
            # raw_type_str is like "struct ContractName.StructName" or "struct StructName"
            struct_name = raw_type_str.replace("struct ", "").strip() if raw_type_str else ""
            # Try qualified name first, then simple name
            members = walker.struct_members.get(struct_name, [])
            if not members and "." in struct_name:
                members = walker.struct_members.get(struct_name.split(".")[-1], [])
            if not members:
                # Last resort: search all keys
                for key in walker.struct_members:
                    if key == struct_name or key.endswith("." + struct_name):
                        members = walker.struct_members[key]
                        break
            if members:
                typ = dict(typ)
                typ["contains"] = [
                    {"name": m["name"], "type": m["type"]} for m in members if m.get("type")
                ]
        elif typ.get("kind") == "enum" and not typ.get("values"):
            enum_name = raw_type_str.replace("enum ", "").strip() if raw_type_str else ""
            vals = walker.enum_values.get(enum_name, [])
            if not vals and "." in enum_name:
                vals = walker.enum_values.get(enum_name.split(".")[-1], [])
            if not vals:
                for key in walker.enum_values:
                    if key == enum_name or key.endswith("." + enum_name):
                        vals = walker.enum_values[key]
                        break
            if vals:
                typ = dict(typ)
                typ["values"] = vals

    if typ:
        entry["type"] = typ

    kind = var.get("kind")

    # Storage pointer for state variables
    if kind in ("state_variable",) and storage_map and name:
        pos = storage_map.get(name)
        if pos:
            entry["pointer"] = {
                "location": "storage",
                "slot": pos["slot"],
                "offset": pos["offset"],
            }

    # Constants are inlined in bytecode — no storage pointer, but we note their kind
    # via the type (no change needed; the ethdebug format doesn't have a "constant" flag).

    # Immutables are written to deployed bytecode at fixed offsets.
    # Without immutableReferences analysis we can't provide a precise pointer.
    # The entry is still useful for its type and declaration info.

    # Must have at least one property
    return entry if entry else None
