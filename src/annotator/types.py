"""
types.py

Solidity AST type nodes → ethdebug type dicts.
"""

from __future__ import annotations

import re
from typing import Optional


def ast_type_to_ethdebug(type_node: Optional[dict], type_str: Optional[str] = None) -> Optional[dict]:
    """Convert a Solidity AST TypeName node to an ethdebug type dict."""
    if type_node is None:
        return _type_str_to_ethdebug(type_str) if type_str else None

    node_kind = type_node.get("nodeType")

    if node_kind == "ElementaryTypeName":
        return _elementary(type_node.get("name", ""))

    if node_kind == "ArrayTypeName":
        base = ast_type_to_ethdebug(type_node.get("baseType"))
        result: dict = {
            "class": "complex",
            "kind": "array",
            "contains": {"type": base} if base else {"type": {"kind": "unknown"}},
        }
        length_node = type_node.get("length")
        if length_node and length_node.get("nodeType") == "Literal":
            result["count"] = int(length_node.get("value", 0))
        return result

    if node_kind == "Mapping":
        key = ast_type_to_ethdebug(type_node.get("keyType"))
        val = ast_type_to_ethdebug(type_node.get("valueType"))
        return {
            "class": "complex",
            "kind": "mapping",
            "contains": {
                "key": {"type": key} if key else {"type": {"kind": "unknown"}},
                "value": {"type": val} if val else {"type": {"kind": "unknown"}},
            },
        }

    if node_kind == "UserDefinedTypeName":
        fallback = type_str or type_node.get("typeDescriptions", {}).get("typeString", "")
        return _type_str_to_ethdebug(fallback, type_node)

    if node_kind == "FunctionTypeName":
        vis = type_node.get("visibility", "internal")
        return {"class": "complex", "kind": "function", "internal": vis != "external"}

    # Fallback: try typeDescriptions.typeString
    ts = type_str or type_node.get("typeDescriptions", {}).get("typeString")
    return _type_str_to_ethdebug(ts)


def _elementary(name: str) -> dict:
    name = name.strip()

    if name == "bool":
        return {"kind": "bool"}
    if name in ("address", "address payable"):
        return {"kind": "address"}
    if name == "string":
        return {"kind": "string"}
    if name == "bytes":
        return {"kind": "bytes"}

    m = re.fullmatch(r"(u?int)(\d*)", name)
    if m:
        bits = int(m.group(2)) if m.group(2) else 256
        return {"kind": m.group(1), "bits": bits}

    m = re.fullmatch(r"bytes(\d+)", name)
    if m:
        return {"kind": "bytes", "bytes": int(m.group(1))}

    m = re.fullmatch(r"(u?fixed)(\d+x\d+)?", name)
    if m:
        kind = m.group(1)
        dims = m.group(2)
        if dims:
            m2 = re.fullmatch(r"(\d+)x(\d+)", dims)
            if m2:
                return {"kind": kind, "bits": int(m2.group(1)), "places": int(m2.group(2))}
        return {"kind": kind, "bits": 128, "places": 18}

    return {"kind": name}


def _type_str_to_ethdebug(ts: Optional[str], node: Optional[dict] = None) -> Optional[dict]:
    if not ts:
        return None

    ts = ts.strip()

    # Strip storage/memory/calldata location suffixes
    for loc in (
        " storage ref",
        " memory ref",
        " calldata ref",
        " storage pointer",
        " memory",
        " calldata",
        " storage",
    ):
        if ts.endswith(loc):
            ts = ts[: -len(loc)]

    # Strip "type(...)" wrapper
    if ts.startswith("type(") and ts.endswith(")"):
        ts = ts[5:-1]

    if ts in ("bool", "address", "address payable", "string", "bytes"):
        return _elementary(ts)

    if re.fullmatch(r"u?int\d*", ts):
        return _elementary(ts)

    if re.fullmatch(r"bytes\d+", ts):
        return _elementary(ts)

    if re.fullmatch(r"u?fixed(\d+x\d+)?", ts):
        return _elementary(ts)

    # Array: T[] or T[N]
    m = re.fullmatch(r"(.+)\[(\d*)\]", ts)
    if m:
        base = _type_str_to_ethdebug(m.group(1).strip())
        result: dict = {
            "class": "complex",
            "kind": "array",
            "contains": {"type": base} if base else {"type": {"kind": "unknown"}},
        }
        if m.group(2):
            result["count"] = int(m.group(2))
        return result

    # Mapping
    # We need to handle nested mappings: split at '=>' but only at the top level.
    # A simple approach: strip outer "mapping(" ... ")"
    if ts.startswith("mapping(") and ts.endswith(")"):
        inner = ts[8:-1]
        depth = 0
        split_at = -1
        for idx, ch in enumerate(inner):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == "=" and depth == 0 and idx + 1 < len(inner) and inner[idx + 1] == ">":
                split_at = idx
                break
        if split_at >= 0:
            key_str = inner[:split_at].strip()
            val_str = inner[split_at + 2 :].strip()
            key = _type_str_to_ethdebug(key_str)
            val = _type_str_to_ethdebug(val_str)
            return {
                "class": "complex",
                "kind": "mapping",
                "contains": {
                    "key": {"type": key} if key else {"type": {"kind": "unknown"}},
                    "value": {"type": val} if val else {"type": {"kind": "unknown"}},
                },
            }

    # Struct
    if ts.startswith("struct "):
        return {"class": "complex", "kind": "struct", "contains": []}

    # Enum
    if ts.startswith("enum "):
        return {"kind": "enum", "values": []}

    # Contract / interface
    if ts.startswith("contract ") or ts.startswith("interface "):
        return {"kind": "contract"}

    # Function
    if ts.startswith("function"):
        return {"class": "complex", "kind": "function", "internal": True}

    # Tuple
    if ts.startswith("(") and ts.endswith(")"):
        return {"class": "complex", "kind": "tuple", "contains": []}

    return None
