"""
ast_walker.py

Solidity AST traversal: collects variables, structs, and enums.
"""

from __future__ import annotations

from typing import Optional

from .types import ast_type_to_ethdebug


def _src_to_range(src: Optional[str]) -> Optional[dict]:
    """Parse "offset:length:fileId" src string."""
    if not src:
        return None
    parts = src.split(":")
    if len(parts) < 3:
        return None
    try:
        return {
            "offset": int(parts[0]),
            "length": int(parts[1]),
            "file_id": int(parts[2]),
        }
    except (ValueError, IndexError):
        return None


def _collect_var_node(
    node: dict,
    kind: str,
    contract: Optional[str],
    function: Optional[str],
    param_index: Optional[int],
) -> Optional[dict]:
    if not isinstance(node, dict):
        return None
    name = node.get("name") or ""
    src = _src_to_range(node.get("src"))
    type_node = node.get("typeName")
    type_desc = node.get("typeDescriptions", {})
    type_str = type_desc.get("typeString")
    ethdebug_type = ast_type_to_ethdebug(type_node, type_str)
    return {
        "name": name,
        "kind": kind,
        "contract": contract,
        "function": function,
        "param_index": param_index,
        "src": src,
        "type": ethdebug_type,
        "type_str": type_str,  # preserved for struct/enum resolution
        "node_id": node.get("id"),
    }


class _ASTWalker:
    """Walks a Solidity AST and collects all variable declarations."""

    def __init__(self) -> None:
        self.variables: list[dict] = []
        # Maps function src range → list of variable dicts for that function
        self.function_vars: dict[tuple, list[dict]] = {}
        # State vars per contract: contract_name → list
        self.contract_state_vars: dict[str, list[dict]] = {}
        # Enum values per qualified name
        self.enum_values: dict[str, list[str]] = {}
        # Struct members per qualified name
        self.struct_members: dict[str, list[dict]] = {}

    def walk(self, node: dict, contract: Optional[str] = None, function: Optional[str] = None) -> None:
        if not isinstance(node, dict):
            return

        nt = node.get("nodeType")

        if nt == "SourceUnit":
            for child in node.get("nodes", []):
                self.walk(child)
            return

        if nt == "ContractDefinition":
            cname = node.get("name")
            self.contract_state_vars.setdefault(cname, [])
            for child in node.get("nodes", []):
                self.walk(child, contract=cname)
            return

        if nt == "StructDefinition":
            qname = f"{contract}.{node.get('name')}" if contract else node.get("name", "")
            members = []
            for m in node.get("members", []):
                members.append(
                    {
                        "name": m.get("name"),
                        "type": ast_type_to_ethdebug(
                            m.get("typeName"),
                            m.get("typeDescriptions", {}).get("typeString"),
                        ),
                    }
                )
            self.struct_members[qname] = members
            return

        if nt == "EnumDefinition":
            qname = f"{contract}.{node.get('name')}" if contract else node.get("name", "")
            vals = [m.get("name") for m in node.get("members", [])]
            self.enum_values[qname] = vals
            return

        if nt == "VariableDeclaration" and node.get("stateVariable"):
            mutability = node.get("mutability", "mutable")
            kind = (
                "constant"
                if mutability == "constant"
                else ("immutable" if mutability == "immutable" else "state_variable")
            )
            v = _collect_var_node(node, kind, contract, None, None)
            if v:
                self.variables.append(v)
                if contract:
                    self.contract_state_vars.setdefault(contract, []).append(v)
            return

        if nt == "FunctionDefinition":
            fname = node.get("name") or node.get("kind", "")
            func_src = _src_to_range(node.get("src"))
            func_vars: list[dict] = []

            # Parameters
            for idx, p in enumerate(node.get("parameters", {}).get("parameters", [])):
                v = _collect_var_node(p, "parameter", contract, fname, idx)
                if v:
                    self.variables.append(v)
                    func_vars.append(v)

            # Return parameters
            for idx, p in enumerate(node.get("returnParameters", {}).get("parameters", [])):
                v = _collect_var_node(p, "return_parameter", contract, fname, idx)
                if v:
                    self.variables.append(v)
                    func_vars.append(v)

            # Body (local variables)
            body = node.get("body")
            if body:
                self._collect_locals(body, contract, fname, func_vars)

            if func_src:
                key = (func_src["file_id"], func_src["offset"], func_src["length"])
                self.function_vars[key] = func_vars

            return

        # Generic recursion
        for value in node.values():
            if isinstance(value, dict):
                self.walk(value, contract, function)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        self.walk(item, contract, function)

    def _collect_locals(
        self, node: dict, contract: Optional[str], function: Optional[str], out: list[dict]
    ) -> None:
        if not isinstance(node, dict):
            return
        nt = node.get("nodeType")
        if nt == "VariableDeclarationStatement":
            for decl in node.get("declarations", []):
                if decl:
                    v = _collect_var_node(decl, "local_variable", contract, function, None)
                    if v:
                        self.variables.append(v)
                        out.append(v)
            # Also recurse into the value expression
            init = node.get("initialValue")
            if init:
                self._collect_locals(init, contract, function, out)
            return
        for value in node.values():
            if isinstance(value, dict):
                self._collect_locals(value, contract, function, out)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        self._collect_locals(item, contract, function, out)
