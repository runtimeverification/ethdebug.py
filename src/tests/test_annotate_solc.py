"""
test_annotate_solc.py

End-to-end tests for the annotator.

Each test defines a self-contained Solidity snippet, compiles it through solc
(optimizer off), runs the annotator, and then uses the DSL from ethdebug_dsl.py
to assert on the resulting ethdebug annotations.

Structure of a typical test:

    def test_something(compile_solidity):
        result = compile_solidity(\"\"\"
            contract C {
                ...
            }
        \"\"\")

        deployed = result.contract("C").deployed()
        deployed.state_var("x").has_type(uint(256)).at_storage_slot(0)

        fn = deployed.in_function("foo")
        fn.param("a").has_type(uint(256))
"""

import pytest

from tests.ethdebug_dsl import (
    AnnotatedResult,
    address_t,
    array,
    bool_t,
    bytes_t,
    bytes1,
    bytes4,
    bytes32,
    contract_t,
    enum_t,
    fixed_bytes,
    function_t,
    int_,
    int256,
    mapping,
    string_t,
    struct,
    tuple_t,
    uint,
    uint8,
    uint16,
    uint32,
    uint256,
)


# ===========================================================================
# 1. Optimizer guard
# ===========================================================================

def test_optimizer_enabled_raises(compile_solidity):
    """The tool must reject output compiled with the optimizer enabled."""
    import json, subprocess

    # Find solc
    from tests.conftest import _SOLC_PATH
    if _SOLC_PATH is None:
        pytest.skip("solc not found")

    from annotator import check_optimizer_disabled

    input_json = {
        "language": "Solidity",
        "sources": {"a.sol": {"content": "pragma solidity ^0.8.28; contract A {}"}},
        "settings": {
            "optimizer": {"enabled": True, "runs": 200},
            "outputSelection": {"*": {"*": ["metadata"]}},
        },
    }
    result = subprocess.run(
        [_SOLC_PATH, "--standard-json"],
        input=json.dumps(input_json).encode(),
        capture_output=True, timeout=30,
    )
    output = json.loads(result.stdout)

    with pytest.raises(RuntimeError, match="Optimizer is enabled"):
        check_optimizer_disabled(output)


# ===========================================================================
# 2. Compilation metadata in the Info object
# ===========================================================================

def test_info_contains_compiler_name(compile_solidity):
    result = compile_solidity("contract C {}")
    info = result.raw.get("ethdebug", {})
    assert info["compilation"]["compiler"]["name"] == "solc"


def test_info_contains_compiler_version(compile_solidity):
    result = compile_solidity("contract C {}")
    info = result.raw.get("ethdebug", {})
    version = info["compilation"]["compiler"]["version"]
    assert version.startswith("0.8.")


def test_info_contains_source_path(compile_solidity):
    result = compile_solidity("contract C {}", filename="my_contract.sol")
    sources = result.raw["ethdebug"]["compilation"]["sources"]
    assert any(s["path"] == "my_contract.sol" for s in sources)


def test_info_source_has_contents(compile_solidity):
    result = compile_solidity("contract C {}", filename="my_contract.sol")
    sources = result.raw["ethdebug"]["compilation"]["sources"]
    src = next(s for s in sources if s["path"] == "my_contract.sol")
    assert "contents" in src
    assert "contract C" in src["contents"]


def test_info_programs_populated(compile_solidity):
    result = compile_solidity("contract C {}")
    programs = result.raw["ethdebug"]["programs"]
    assert len(programs) >= 2  # create + call for C


# ===========================================================================
# 3. State variables – elementary types
# ===========================================================================

def test_state_var_uint256(compile_solidity):
    result = compile_solidity("""
        contract C {
            uint256 public x;
        }
    """)
    result.contract("C").deployed().state_var("x") \
        .has_type(uint256) \
        .at_storage_slot(0)


def test_state_var_address(compile_solidity):
    result = compile_solidity("""
        contract C {
            address public owner;
        }
    """)
    result.contract("C").deployed().state_var("owner") \
        .has_type(address_t) \
        .at_storage_slot(0)


def test_state_var_bool(compile_solidity):
    result = compile_solidity("""
        contract C {
            bool public paused;
        }
    """)
    result.contract("C").deployed().state_var("paused") \
        .has_type(bool_t) \
        .at_storage_slot(0)


def test_state_var_string(compile_solidity):
    result = compile_solidity("""
        contract C {
            string public name;
        }
    """)
    result.contract("C").deployed().state_var("name") \
        .has_type(string_t) \
        .at_storage_slot(0)


def test_state_var_bytes_dynamic(compile_solidity):
    result = compile_solidity("""
        contract C {
            bytes public data;
        }
    """)
    result.contract("C").deployed().state_var("data") \
        .has_type(bytes_t) \
        .at_storage_slot(0)


def test_state_var_bytes32(compile_solidity):
    result = compile_solidity("""
        contract C {
            bytes32 public root;
        }
    """)
    result.contract("C").deployed().state_var("root") \
        .has_type(bytes32) \
        .at_storage_slot(0)


def test_state_var_bytes4(compile_solidity):
    result = compile_solidity("""
        contract C {
            bytes4 public selector;
        }
    """)
    result.contract("C").deployed().state_var("selector") \
        .has_type(bytes4) \
        .at_storage_slot(0)


def test_state_var_int256(compile_solidity):
    result = compile_solidity("""
        contract C {
            int256 public delta;
        }
    """)
    result.contract("C").deployed().state_var("delta") \
        .has_type(int256) \
        .at_storage_slot(0)


def test_state_var_uint8(compile_solidity):
    result = compile_solidity("""
        contract C {
            uint8 public decimals;
        }
    """)
    result.contract("C").deployed().state_var("decimals") \
        .has_type(uint8) \
        .at_storage_slot(0)


# ===========================================================================
# 4. Constants
# ===========================================================================

def test_constant_uint256(compile_solidity):
    result = compile_solidity("""
        contract C {
            uint256 public constant MAX = 1000;
        }
    """)
    result.contract("C").deployed().state_var("MAX") \
        .has_type(uint256) \
        .is_constant()


def test_constant_address(compile_solidity):
    result = compile_solidity("""
        contract C {
            address public constant ZERO = address(0);
        }
    """)
    result.contract("C").deployed().state_var("ZERO") \
        .has_type(address_t) \
        .is_constant()


def test_constant_bool(compile_solidity):
    result = compile_solidity("""
        contract C {
            bool public constant FLAG = true;
        }
    """)
    result.contract("C").deployed().state_var("FLAG") \
        .has_type(bool_t) \
        .is_constant()


def test_constant_bytes32(compile_solidity):
    result = compile_solidity("""
        contract C {
            bytes32 public constant DOMAIN = keccak256("domain");
        }
    """)
    result.contract("C").deployed().state_var("DOMAIN") \
        .has_type(bytes32) \
        .is_constant()


# ===========================================================================
# 5. Immutables
# ===========================================================================

def test_immutable_uint256(compile_solidity):
    result = compile_solidity("""
        contract C {
            uint256 public immutable creationTime;
            constructor() { creationTime = block.timestamp; }
        }
    """)
    result.contract("C").deployed().state_var("creationTime") \
        .has_type(uint256) \
        .is_immutable()


def test_immutable_address(compile_solidity):
    result = compile_solidity("""
        contract C {
            address public immutable owner;
            constructor(address _owner) { owner = _owner; }
        }
    """)
    result.contract("C").deployed().state_var("owner") \
        .has_type(address_t) \
        .is_immutable()


def test_immutable_bool(compile_solidity):
    result = compile_solidity("""
        contract C {
            bool public immutable locked;
            constructor(bool _locked) { locked = _locked; }
        }
    """)
    result.contract("C").deployed().state_var("locked") \
        .has_type(bool_t) \
        .is_immutable()


# ===========================================================================
# 6. Complex state variable types
# ===========================================================================

def test_state_var_mapping(compile_solidity):
    result = compile_solidity("""
        contract C {
            mapping(address => uint256) public balances;
        }
    """)
    result.contract("C").deployed().state_var("balances") \
        .has_type(mapping(address_t, uint256)) \
        .at_storage_slot(0)


def test_state_var_nested_mapping(compile_solidity):
    result = compile_solidity("""
        contract C {
            mapping(address => mapping(address => uint256)) public allowances;
        }
    """)
    result.contract("C").deployed().state_var("allowances") \
        .has_type(mapping(address_t, mapping(address_t, uint256))) \
        .at_storage_slot(0)


def test_state_var_dynamic_array(compile_solidity):
    result = compile_solidity("""
        contract C {
            address[] public users;
        }
    """)
    result.contract("C").deployed().state_var("users") \
        .has_type(array(address_t)) \
        .at_storage_slot(0)


def test_state_var_fixed_array(compile_solidity):
    result = compile_solidity("""
        contract C {
            uint256[4] public slots;
        }
    """)
    result.contract("C").deployed().state_var("slots") \
        .has_type(array(uint256, count=4)) \
        .at_storage_slot(0)


def test_state_var_struct(compile_solidity):
    result = compile_solidity("""
        struct Point { int256 x; int256 y; }
        contract C {
            Point public origin;
        }
    """)
    result.contract("C").deployed().state_var("origin") \
        .has_type(struct(members={"x": int256, "y": int256})) \
        .at_storage_slot(0)


def test_state_var_enum(compile_solidity):
    result = compile_solidity("""
        enum Status { Pending, Active, Inactive }
        contract C {
            Status public status;
        }
    """)
    result.contract("C").deployed().state_var("status") \
        .has_type(enum_t(values=["Pending", "Active", "Inactive"])) \
        .at_storage_slot(0)


def test_state_var_mapping_to_struct(compile_solidity):
    result = compile_solidity("""
        struct Profile { string name; uint256 age; }
        contract C {
            mapping(address => Profile) public profiles;
        }
    """)
    result.contract("C").deployed().state_var("profiles") \
        .has_type(mapping(address_t, struct())) \
        .at_storage_slot(0)


# ===========================================================================
# 7. Multiple state variables – storage slot ordering
# ===========================================================================

def test_storage_slot_ordering(compile_solidity):
    result = compile_solidity("""
        contract C {
            uint256 public a;
            uint256 public b;
            uint256 public c;
        }
    """)
    deployed = result.contract("C").deployed()
    deployed.state_var("a").at_storage_slot(0)
    deployed.state_var("b").at_storage_slot(1)
    deployed.state_var("c").at_storage_slot(2)


def test_storage_slot_packing(compile_solidity):
    """uint128 variables pack two-to-a-slot."""
    result = compile_solidity("""
        contract C {
            uint128 public lo;
            uint128 public hi;
        }
    """)
    deployed = result.contract("C").deployed()
    deployed.state_var("lo").at_storage_slot(0, offset=0)
    deployed.state_var("hi").at_storage_slot(0, offset=16)


def test_mixed_constant_and_storage(compile_solidity):
    """Constants do not occupy storage; regular vars are slotted from 0."""
    result = compile_solidity("""
        contract C {
            uint256 public constant VERSION = 1;
            address public immutable owner;
            uint256 public counter;
            constructor(address _o) { owner = _o; }
        }
    """)
    deployed = result.contract("C").deployed()
    deployed.state_var("VERSION").is_constant()
    deployed.state_var("owner").is_immutable()
    deployed.state_var("counter").at_storage_slot(0)


# ===========================================================================
# 8. Function parameters
# ===========================================================================

def test_function_single_param(compile_solidity):
    result = compile_solidity("""
        contract C {
            function foo(uint256 x) external pure returns (uint256) {
                return x;
            }
        }
    """)
    result.contract("C").deployed() \
        .in_function("foo") \
        .param("x").has_type(uint256)


def test_function_multiple_params(compile_solidity):
    result = compile_solidity("""
        contract C {
            function transfer(address to, uint256 amount) external {
            }
        }
    """)
    fn = result.contract("C").deployed().in_function("transfer")
    fn.param("to").has_type(address_t)
    fn.param("amount").has_type(uint256)


def test_function_bool_param(compile_solidity):
    result = compile_solidity("""
        contract C {
            function setFlag(bool enabled) external {
            }
        }
    """)
    result.contract("C").deployed() \
        .in_function("setFlag") \
        .param("enabled").has_type(bool_t)


def test_function_bytes_param(compile_solidity):
    result = compile_solidity("""
        contract C {
            function process(bytes calldata data) external {
            }
        }
    """)
    result.contract("C").deployed() \
        .in_function("process") \
        .param("data").has_type(bytes_t)


def test_function_string_param(compile_solidity):
    result = compile_solidity("""
        contract C {
            function greet(string calldata name) external pure returns (string memory) {
                return name;
            }
        }
    """)
    result.contract("C").deployed() \
        .in_function("greet") \
        .param("name").has_type(string_t)


def test_function_struct_param(compile_solidity):
    result = compile_solidity("""
        struct Point { int256 x; int256 y; }
        contract C {
            function move(Point memory p) external pure returns (int256) {
                return p.x;
            }
        }
    """)
    result.contract("C").deployed() \
        .in_function("move") \
        .param("p").has_type(struct())


def test_function_array_param(compile_solidity):
    result = compile_solidity("""
        contract C {
            function sum(uint256[] calldata vals) external pure returns (uint256 total) {
                for (uint256 i = 0; i < vals.length; i++) { total += vals[i]; }
            }
        }
    """)
    result.contract("C").deployed() \
        .in_function("sum") \
        .param("vals").has_type(array(uint256))


def test_function_address_payable_param(compile_solidity):
    result = compile_solidity("""
        contract C {
            function send(address payable recipient, uint256 amount) external {
            }
        }
    """)
    fn = result.contract("C").deployed().in_function("send")
    fn.param("recipient").has_type(address_t)
    fn.param("amount").has_type(uint256)


def test_function_bytes32_param(compile_solidity):
    result = compile_solidity("""
        contract C {
            function verify(bytes32 hash, bytes32 sig) external pure returns (bool) {
                return hash == sig;
            }
        }
    """)
    fn = result.contract("C").deployed().in_function("verify")
    fn.param("hash").has_type(bytes32)
    fn.param("sig").has_type(bytes32)


def test_function_enum_param(compile_solidity):
    result = compile_solidity("""
        enum Direction { North, South, East, West }
        contract C {
            function move(Direction d) external pure returns (uint8) {
                return uint8(d);
            }
        }
    """)
    result.contract("C").deployed() \
        .in_function("move") \
        .param("d").has_type(enum_t())


def test_function_uint_variants(compile_solidity):
    result = compile_solidity("""
        contract C {
            function f(uint8 a, uint16 b, uint32 c, uint256 d) external pure
                returns (uint256) { return a + b + c + d; }
        }
    """)
    fn = result.contract("C").deployed().in_function("f")
    fn.param("a").has_type(uint8)
    fn.param("b").has_type(uint16)
    fn.param("c").has_type(uint32)
    fn.param("d").has_type(uint256)


def test_function_int_variants(compile_solidity):
    result = compile_solidity("""
        contract C {
            function f(int8 a, int256 b) external pure returns (int256) { return a + b; }
        }
    """)
    fn = result.contract("C").deployed().in_function("f")
    fn.param("a").has_type(int_(8))
    fn.param("b").has_type(int256)


# ===========================================================================
# 9. Return parameters
# ===========================================================================

def test_named_return_parameter(compile_solidity):
    result = compile_solidity("""
        contract C {
            function compute(uint256 x) external pure returns (uint256 result) {
                result = x * 2;
            }
        }
    """)
    result.contract("C").deployed() \
        .in_function("compute") \
        .returns("result").has_type(uint256)


def test_multiple_named_returns(compile_solidity):
    result = compile_solidity("""
        contract C {
            function divide(uint256 a, uint256 b)
                external pure
                returns (uint256 quotient, uint256 remainder)
            {
                quotient = a / b;
                remainder = a % b;
            }
        }
    """)
    fn = result.contract("C").deployed().in_function("divide")
    fn.returns("quotient").has_type(uint256)
    fn.returns("remainder").has_type(uint256)


def test_named_return_bool(compile_solidity):
    result = compile_solidity("""
        contract C {
            function check(uint256 x) external pure returns (bool ok) {
                ok = x > 0;
            }
        }
    """)
    result.contract("C").deployed() \
        .in_function("check") \
        .returns("ok").has_type(bool_t)


def test_named_return_address(compile_solidity):
    result = compile_solidity("""
        contract C {
            address public owner;
            function getOwner() external view returns (address addr) {
                addr = owner;
            }
        }
    """)
    result.contract("C").deployed() \
        .in_function("getOwner") \
        .returns("addr").has_type(address_t)


# ===========================================================================
# 10. Local variables
# ===========================================================================

def test_local_variable_uint256(compile_solidity):
    result = compile_solidity("""
        contract C {
            function compute(uint256 x) external pure returns (uint256) {
                uint256 doubled = x * 2;
                return doubled;
            }
        }
    """)
    result.contract("C").deployed() \
        .in_function("compute") \
        .local("doubled").has_type(uint256)


def test_local_variable_bool(compile_solidity):
    result = compile_solidity("""
        contract C {
            function check() external pure returns (bool) {
                bool flag = true;
                return flag;
            }
        }
    """)
    result.contract("C").deployed() \
        .in_function("check") \
        .local("flag").has_type(bool_t)


def test_local_variable_address(compile_solidity):
    result = compile_solidity("""
        contract C {
            function caller() external view returns (address) {
                address who = msg.sender;
                return who;
            }
        }
    """)
    result.contract("C").deployed() \
        .in_function("caller") \
        .local("who").has_type(address_t)


def test_local_variable_string(compile_solidity):
    result = compile_solidity("""
        contract C {
            function greet() external pure returns (string memory) {
                string memory msg = "hello";
                return msg;
            }
        }
    """)
    result.contract("C").deployed() \
        .in_function("greet") \
        .local("msg").has_type(string_t)


def test_local_variable_struct(compile_solidity):
    result = compile_solidity("""
        struct Point { int256 x; int256 y; }
        contract C {
            function origin() external pure returns (int256) {
                Point memory p = Point(0, 0);
                return p.x;
            }
        }
    """)
    result.contract("C").deployed() \
        .in_function("origin") \
        .local("p").has_type(struct())


def test_local_variable_bytes32(compile_solidity):
    result = compile_solidity("""
        contract C {
            function hashIt(string calldata s) external pure returns (bytes32) {
                bytes32 h = keccak256(bytes(s));
                return h;
            }
        }
    """)
    result.contract("C").deployed() \
        .in_function("hashIt") \
        .local("h").has_type(bytes32)


def test_local_variable_low_level_call(compile_solidity):
    result = compile_solidity("""
        contract C {
            function callTarget(address target) external payable returns (bool) {
                (bool ok,) = target.call{value: msg.value}("");
                return ok;
            }
        }
    """)
    result.contract("C").deployed() \
        .in_function("callTarget") \
        .local("ok").has_type(bool_t)


# ===========================================================================
# 11. Declaration source ranges
# ===========================================================================

def test_state_var_has_declaration(compile_solidity):
    result = compile_solidity("""
        contract C {
            uint256 public x;
        }
    """)
    result.contract("C").deployed().state_var("x").has_declaration()


def test_function_param_has_declaration(compile_solidity):
    result = compile_solidity("""
        contract C {
            function foo(uint256 val) external pure returns (uint256) { return val; }
        }
    """)
    result.contract("C").deployed() \
        .in_function("foo") \
        .param("val").has_declaration()


# ===========================================================================
# 12. Multiple contracts in one compilation unit
# ===========================================================================

def test_two_contracts_independent(compile_solidity):
    result = compile_solidity("""
        contract Token {
            uint256 public totalSupply;
            mapping(address => uint256) public balances;
        }

        contract Vault {
            address public asset;
            uint256 public reserve;
        }
    """)
    token = result.contract("Token").deployed()
    token.state_var("totalSupply").has_type(uint256).at_storage_slot(0)
    token.state_var("balances").has_type(mapping(address_t, uint256)).at_storage_slot(1)

    vault = result.contract("Vault").deployed()
    vault.state_var("asset").has_type(address_t).at_storage_slot(0)
    vault.state_var("reserve").has_type(uint256).at_storage_slot(1)


def test_contract_names_discovered(compile_solidity):
    result = compile_solidity("""
        contract A {}
        contract B {}
        contract C {}
    """)
    names = result.contract_names()
    assert "A" in names
    assert "B" in names
    assert "C" in names


# ===========================================================================
# 13. Creation vs deployed bytecode programs
# ===========================================================================

def test_creation_program_exists(compile_solidity):
    result = compile_solidity("""
        contract C {
            uint256 public x;
            constructor() { x = 42; }
        }
    """)
    creation = result.contract("C").creation()
    assert creation.instruction_count() > 0


def test_deployed_program_exists(compile_solidity):
    result = compile_solidity("""
        contract C {
            uint256 public x;
        }
    """)
    deployed = result.contract("C").deployed()
    assert deployed.instruction_count() > 0


def test_state_vars_in_creation_context(compile_solidity):
    """State variables should also appear in the creation bytecode context."""
    result = compile_solidity("""
        contract C {
            uint256 public x;
            constructor() { x = 1; }
        }
    """)
    result.contract("C").creation().state_var("x") \
        .has_type(uint256) \
        .at_storage_slot(0)


# ===========================================================================
# 14. Instructions carry source ranges
# ===========================================================================

def test_instructions_have_source_ranges(compile_solidity):
    result = compile_solidity("""
        contract C {
            uint256 public x;
            function set(uint256 v) external { x = v; }
        }
    """)
    deployed = result.contract("C").deployed()
    # At least some instructions should have a code context
    mapped = deployed.instructions_with_source()
    assert len(mapped) > 0


# ===========================================================================
# 15. Complex real-world contract
# ===========================================================================

def test_erc20_like_contract(compile_solidity):
    result = compile_solidity("""
        contract ERC20 {
            string  public name;
            string  public symbol;
            uint8   public decimals;
            uint256 public totalSupply;

            mapping(address => uint256) public balanceOf;
            mapping(address => mapping(address => uint256)) public allowance;

            address public immutable deployer;

            constructor(
                string memory _name,
                string memory _symbol,
                uint8 _decimals,
                uint256 _totalSupply
            ) {
                deployer    = msg.sender;
                name        = _name;
                symbol      = _symbol;
                decimals    = _decimals;
                totalSupply = _totalSupply;
                balanceOf[msg.sender] = _totalSupply;
            }

            function transfer(address to, uint256 amount)
                external returns (bool success)
            {
                require(balanceOf[msg.sender] >= amount, "insufficient");
                balanceOf[msg.sender] -= amount;
                balanceOf[to] += amount;
                bool ok = true;
                success = ok;
                return success;
            }

            function approve(address spender, uint256 amount)
                external returns (bool)
            {
                allowance[msg.sender][spender] = amount;
                return true;
            }
        }
    """)

    deployed = result.contract("ERC20").deployed()

    # State variables
    deployed.state_var("name").has_type(string_t).at_storage_slot(0)
    deployed.state_var("symbol").has_type(string_t).at_storage_slot(1)
    deployed.state_var("decimals").has_type(uint8).at_storage_slot(2)
    deployed.state_var("totalSupply").has_type(uint256).at_storage_slot(3)
    deployed.state_var("balanceOf").has_type(mapping(address_t, uint256)).at_storage_slot(4)
    deployed.state_var("allowance") \
        .has_type(mapping(address_t, mapping(address_t, uint256))) \
        .at_storage_slot(5)
    deployed.state_var("deployer").has_type(address_t).is_immutable()

    # Constructor parameters (in creation bytecode)
    ctor = result.contract("ERC20").creation().in_function("constructor")
    ctor.param("_name").has_type(string_t)
    ctor.param("_symbol").has_type(string_t)
    ctor.param("_decimals").has_type(uint8)
    ctor.param("_totalSupply").has_type(uint256)

    # transfer function
    transfer = deployed.in_function("transfer")
    transfer.param("to").has_type(address_t)
    transfer.param("amount").has_type(uint256)
    transfer.returns("success").has_type(bool_t)
    transfer.local("ok").has_type(bool_t)

    # approve function
    approve = deployed.in_function("approve")
    approve.param("spender").has_type(address_t)
    approve.param("amount").has_type(uint256)
