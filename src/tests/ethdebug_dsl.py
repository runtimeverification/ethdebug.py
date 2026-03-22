"""
ethdebug_dsl.py

Domain-specific embedded language for asserting on ethdebug data.

Example usage:

    result = compile_solidity(\"\"\"
        contract C {
            uint256 public x;
            address public constant ADMIN = address(0);
            function set(uint256 v) external { x = v; }
        }
    \"\"\")

    deployed = result.contract("C").deployed()
    deployed.state_var("x").has_type(uint(256)).at_storage_slot(0)
    deployed.state_var("ADMIN").has_type(address_t).is_constant()

    fn = deployed.in_function("set")
    fn.param("v").has_type(uint(256))
"""

from __future__ import annotations

from typing import Any, Optional


# ---------------------------------------------------------------------------
# Type specification objects
# ---------------------------------------------------------------------------

class TypeSpec:
    """Represents an expected ethdebug type for use in assertions.

    Matching is done as a *subset* check: every key in the TypeSpec dict
    must be present and equal in the actual type, but the actual type may
    have additional keys.  This allows ergonomic partial matching.
    """

    def __init__(self, spec: dict) -> None:
        self._spec = spec

    def _as_dict(self) -> dict:
        return self._spec

    def __repr__(self) -> str:
        return f"TypeSpec({self._spec})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, TypeSpec):
            return self._spec == other._spec
        return NotImplemented


# --- Elementary type singletons and factories ---

def uint(bits: int) -> TypeSpec:
    return TypeSpec({"kind": "uint", "bits": bits})

def int_(bits: int) -> TypeSpec:
    return TypeSpec({"kind": "int", "bits": bits})

def fixed_bytes(n: int) -> TypeSpec:
    """bytesN (fixed-size byte arrays, e.g. bytes32)."""
    return TypeSpec({"kind": "bytes", "bytes": n})

def ufixed(bits: int, places: int) -> TypeSpec:
    return TypeSpec({"kind": "ufixed", "bits": bits, "places": places})

def fixed(bits: int, places: int) -> TypeSpec:
    return TypeSpec({"kind": "fixed", "bits": bits, "places": places})

# Singletons for the unparameterised elementary types
bool_t   = TypeSpec({"kind": "bool"})
address_t = TypeSpec({"kind": "address"})
string_t  = TypeSpec({"kind": "string"})
bytes_t   = TypeSpec({"kind": "bytes"})
contract_t = TypeSpec({"kind": "contract"})

# Convenient aliases for the most common uint widths
uint256 = uint(256)
uint128 = uint(128)
uint64  = uint(64)
uint32  = uint(32)
uint16  = uint(16)
uint8   = uint(8)

int256  = int_(256)
int128  = int_(128)
int64   = int_(64)
int32   = int_(32)
int16   = int_(16)
int8    = int_(8)

bytes32 = fixed_bytes(32)
bytes16 = fixed_bytes(16)
bytes4  = fixed_bytes(4)
bytes1  = fixed_bytes(1)


# --- Complex type factories ---

def mapping(key: TypeSpec, value: TypeSpec) -> TypeSpec:
    return TypeSpec({
        "class": "complex",
        "kind": "mapping",
        "contains": {
            "key":   {"type": key._as_dict()},
            "value": {"type": value._as_dict()},
        },
    })

def array(element: TypeSpec, count: Optional[int] = None) -> TypeSpec:
    spec: dict = {
        "class": "complex",
        "kind": "array",
        "contains": {"type": element._as_dict()},
    }
    if count is not None:
        spec["count"] = count
    return TypeSpec(spec)

def struct(name: Optional[str] = None, members: Optional[dict[str, TypeSpec]] = None) -> TypeSpec:
    """Match a struct type.  ``name`` is ignored (ethdebug doesn't store it in kind).
    ``members`` is a {field_name: TypeSpec} dict for deeper checking."""
    spec: dict = {"class": "complex", "kind": "struct"}
    if members is not None:
        spec["contains"] = [
            {"name": k, "type": v._as_dict()} for k, v in members.items()
        ]
    return TypeSpec(spec)

def enum_t(values: Optional[list[str]] = None) -> TypeSpec:
    spec: dict = {"kind": "enum"}
    if values is not None:
        spec["values"] = values
    return TypeSpec(spec)

def function_t(internal: bool = True) -> TypeSpec:
    return TypeSpec({"class": "complex", "kind": "function", "internal": internal})

def tuple_t() -> TypeSpec:
    return TypeSpec({"class": "complex", "kind": "tuple"})


# ---------------------------------------------------------------------------
# Type matching
# ---------------------------------------------------------------------------

def _type_matches(actual: Optional[dict], expected: TypeSpec) -> bool:
    """Partial subset match: every key in expected must appear with the same
    value in actual.  Nested dicts are matched recursively."""
    return _dict_subset(actual, expected._as_dict())


def _dict_subset(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False
        return all(
            k in actual and _dict_subset(actual[k], expected[k])
            for k in expected
        )
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return False
        if len(expected) != len(actual):
            return False
        return all(_dict_subset(a, e) for a, e in zip(actual, expected))
    return actual == expected


# ---------------------------------------------------------------------------
# AST helpers (extract function source ranges from annotated output)
# ---------------------------------------------------------------------------

def _extract_function_ranges(annotated: dict) -> dict[str, dict[str, tuple]]:
    """Return {contract_name: {func_name: (file_id, offset, length)}}."""
    result: dict[str, dict[str, tuple]] = {}

    def _src_to_tuple(src: Optional[str]) -> Optional[tuple]:
        if not src:
            return None
        parts = src.split(":")
        if len(parts) < 3:
            return None
        try:
            return (int(parts[2]), int(parts[0]), int(parts[1]))
        except ValueError:
            return None

    for _path, src_data in annotated.get("sources", {}).items():
        ast = src_data.get("ast")
        if not ast:
            continue
        for node in ast.get("nodes", []):
            if node.get("nodeType") == "ContractDefinition":
                cname = node.get("name", "")
                result.setdefault(cname, {})
                for child in node.get("nodes", []):
                    if child.get("nodeType") == "FunctionDefinition":
                        fname = child.get("name") or child.get("kind", "")
                        t = _src_to_tuple(child.get("src"))
                        if t:
                            result[cname][fname] = t

    return result


def _range_contains(outer: tuple, inner: tuple) -> bool:
    """True if outer (file_id, offset, length) fully contains inner."""
    fid_o, off_o, len_o = outer
    fid_i, off_i, len_i = inner
    if fid_o != fid_i:
        return False
    return off_o <= off_i and (off_i + len_i) <= (off_o + len_o)


# ---------------------------------------------------------------------------
# VariableView – leaf of the DSL chain
# ---------------------------------------------------------------------------

class VariableView:
    """Wraps a single variable entry in the ethdebug output and provides
    assertion helpers that return ``self`` for chaining."""

    def __init__(self, identifier: str, data: dict, context_desc: str) -> None:
        self._id = identifier
        self._data = data
        self._desc = context_desc

    # --- type assertions ---

    def has_type(self, expected: TypeSpec) -> "VariableView":
        actual = self._data.get("type")
        if not _type_matches(actual, expected):
            raise AssertionError(
                f"{self._desc}: expected type {expected}, got {actual}"
            )
        return self

    # --- location / pointer assertions ---

    def at_storage_slot(self, slot: int, offset: int = 0) -> "VariableView":
        ptr = self._data.get("pointer")
        if ptr is None:
            raise AssertionError(
                f"{self._desc}: expected storage pointer at slot {slot} "
                "but no pointer is present"
            )
        if ptr.get("location") != "storage":
            raise AssertionError(
                f"{self._desc}: expected location 'storage', "
                f"got {ptr.get('location')!r}"
            )
        actual_slot = ptr.get("slot")
        if actual_slot != slot:
            raise AssertionError(
                f"{self._desc}: expected storage slot {slot}, "
                f"got {actual_slot}"
            )
        actual_offset = ptr.get("offset", 0)
        if actual_offset != offset:
            raise AssertionError(
                f"{self._desc}: expected storage offset {offset}, "
                f"got {actual_offset}"
            )
        return self

    def is_constant(self) -> "VariableView":
        """Constants are inlined; they must have no storage pointer."""
        ptr = self._data.get("pointer")
        if ptr is not None:
            raise AssertionError(
                f"{self._desc}: constant variable should have no storage pointer, "
                f"but found {ptr}"
            )
        return self

    def is_immutable(self) -> "VariableView":
        """Immutables are written to the deployed bytecode; no storage pointer."""
        ptr = self._data.get("pointer")
        if ptr is not None:
            raise AssertionError(
                f"{self._desc}: immutable variable should have no storage pointer, "
                f"but found {ptr}"
            )
        return self

    def has_declaration(self) -> "VariableView":
        decl = self._data.get("declaration")
        if decl is None:
            raise AssertionError(
                f"{self._desc}: expected a declaration source range, but none found"
            )
        source = decl.get("source")
        rng = decl.get("range")
        if source is None or rng is None:
            raise AssertionError(
                f"{self._desc}: declaration is malformed: {decl}"
            )
        return self


# ---------------------------------------------------------------------------
# FunctionScope – narrows to a particular function's instruction contexts
# ---------------------------------------------------------------------------

class FunctionScope:
    """Provides variable look-up scoped to a single function's body."""

    def __init__(
        self,
        func_name: str,
        contract_name: str,
        program: dict,
        func_ranges: dict[str, tuple],
    ) -> None:
        self._func_name = func_name
        self._contract = contract_name
        self._program = program
        self._func_ranges = func_ranges
        self._vars: dict[str, dict] = self._collect()

    def _collect(self) -> dict[str, dict]:
        """Collect unique variables from instruction contexts that belong to
        this function's source range.  Falls back to all instruction vars if
        the function range cannot be determined."""
        func_range = self._func_ranges.get(self._func_name)
        seen: dict[str, dict] = {}

        for instr in self._program.get("instructions", []):
            ctx = instr.get("context", {})
            fvars = ctx.get("variables", [])
            if not fvars:
                continue

            # If we have a function range, only include instructions inside it
            if func_range is not None:
                code = ctx.get("code", {})
                rng = code.get("range", {})
                src = code.get("source", {})
                fid = src.get("id", -1)
                off = rng.get("offset", -1)
                lng = rng.get("length", 0)
                instr_range = (fid, off, lng)
                if off < 0 or not _range_contains(func_range, instr_range):
                    continue

            for v in fvars:
                ident = v.get("identifier")
                if ident and ident not in seen:
                    seen[ident] = v

        return seen

    def _get(self, identifier: str) -> VariableView:
        v = self._vars.get(identifier)
        if v is None:
            available = sorted(self._vars.keys())
            raise AssertionError(
                f"Variable '{identifier}' not found in function "
                f"'{self._func_name}' of {self._contract}. "
                f"Available identifiers: {available}"
            )
        return VariableView(
            identifier, v,
            f"'{identifier}' in {self._contract}.{self._func_name}"
        )

    def param(self, identifier: str) -> VariableView:
        """Assert on a function parameter by name."""
        return self._get(identifier)

    def returns(self, identifier: str) -> VariableView:
        """Assert on a named return parameter."""
        return self._get(identifier)

    def local(self, identifier: str) -> VariableView:
        """Assert on a local variable."""
        return self._get(identifier)

    def has_variable(self, identifier: str) -> VariableView:
        """Assert that any function-level variable with this name exists."""
        return self._get(identifier)

    def variable_identifiers(self) -> list[str]:
        """Return all found variable identifiers (useful in debugging)."""
        return sorted(self._vars.keys())


# ---------------------------------------------------------------------------
# ProgramView – one bytecode program (create or call environment)
# ---------------------------------------------------------------------------

class ProgramView:
    def __init__(
        self,
        contract_name: str,
        environment: str,
        program: dict,
        func_ranges: dict[str, tuple],
    ) -> None:
        self._contract = contract_name
        self._environment = environment
        self._program = program
        self._func_ranges = func_ranges

    # --- state variable assertions ---

    def state_var(self, identifier: str) -> VariableView:
        """Assert on a state variable present in the program's initial context."""
        vars_ = self._program.get("context", {}).get("variables", [])
        for v in vars_:
            if v.get("identifier") == identifier:
                return VariableView(
                    identifier, v,
                    f"state var '{identifier}' in {self._contract}/{self._environment}"
                )
        available = [v.get("identifier") for v in vars_]
        raise AssertionError(
            f"State variable '{identifier}' not found in initial context of "
            f"{self._contract}/{self._environment}. "
            f"Available: {available}"
        )

    def state_var_identifiers(self) -> list[str]:
        vars_ = self._program.get("context", {}).get("variables", [])
        return [v.get("identifier") for v in vars_]

    # --- function scope ---

    def in_function(self, name: str) -> FunctionScope:
        """Return a FunctionScope that narrows assertions to ``name``'s body."""
        return FunctionScope(
            func_name=name,
            contract_name=self._contract,
            program=self._program,
            func_ranges=self._func_ranges,
        )

    # --- instruction-level helpers ---

    def instruction_count(self) -> int:
        return len(self._program.get("instructions", []))

    def instructions_with_source(self) -> list[dict]:
        return [
            i for i in self._program.get("instructions", [])
            if i.get("context", {}).get("code")
        ]


# ---------------------------------------------------------------------------
# ContractView
# ---------------------------------------------------------------------------

class ContractView:
    def __init__(
        self,
        name: str,
        annotated: dict,
        func_ranges: dict[str, dict[str, tuple]],
    ) -> None:
        self._name = name
        self._annotated = annotated
        self._func_ranges = func_ranges

    def deployed(self) -> ProgramView:
        """The runtime (call) bytecode program."""
        return self._get_program("call")

    def creation(self) -> ProgramView:
        """The creation bytecode program."""
        return self._get_program("create")

    def _get_program(self, environment: str) -> ProgramView:
        for prog in self._annotated.get("ethdebug", {}).get("programs", []):
            if (
                prog.get("contract", {}).get("name") == self._name
                and prog.get("environment") == environment
            ):
                return ProgramView(
                    self._name,
                    environment,
                    prog,
                    self._func_ranges.get(self._name, {}),
                )
        available = [
            f"{p.get('contract',{}).get('name')}/{p.get('environment')}"
            for p in self._annotated.get("ethdebug", {}).get("programs", [])
        ]
        raise AssertionError(
            f"No '{environment}' program found for contract '{self._name}'. "
            f"Available programs: {available}"
        )


# ---------------------------------------------------------------------------
# AnnotatedResult – root of the DSL
# ---------------------------------------------------------------------------

class AnnotatedResult:
    """Root object returned by the ``compile_solidity`` fixture.

    Use ``.contract(name)`` to navigate to a specific contract, then
    ``.deployed()`` / ``.creation()`` for the runtime / creation bytecode,
    and then use assertion helpers on the resulting :class:`ProgramView`.
    """

    def __init__(self, annotated: dict) -> None:
        self._annotated = annotated
        self._func_ranges = _extract_function_ranges(annotated)

    def contract(self, name: str) -> ContractView:
        return ContractView(name, self._annotated, self._func_ranges)

    def contract_names(self) -> list[str]:
        names: list[str] = []
        for prog in self._annotated.get("ethdebug", {}).get("programs", []):
            n = prog.get("contract", {}).get("name")
            if n and n not in names:
                names.append(n)
        return names

    @property
    def raw(self) -> dict:
        """Access the full annotated output dict."""
        return self._annotated
