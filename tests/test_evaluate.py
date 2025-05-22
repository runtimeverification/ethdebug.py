import pytest
from unittest.mock import AsyncMock
from ethdebug.evaluate import EvaluateOptions, evaluate
from ethdebug.data import Data
from ethdebug.dereference.cursor import Region, Regions
from ethdebug.format.data.unsigned_schema import EthdebugFormatDataUnsigned
from ethdebug.format.data.value_schema import EthdebugFormatDataValue
from ethdebug.format.pointer.expression_schema import Arithmetic, Constant, EthdebugFormatPointerExpression, Literal, Lookup, Operands, Reference, Resize, Variable
from ethdebug.format.pointer.identifier_schema import EthdebugFormatPointerIdentifier
from ethdebug.machine import MachineState

from tests.mock_machine import MockCalldata, MockCode, MockMemory, MockReturndata, MockStack, MockState, MockStorage, MockTransient

@pytest.fixture
def state() -> MachineState:
    return MockState(
        trace_index=AsyncMock(return_value=0),
        opcode=AsyncMock(return_value="PUSH1"),
        program_counter=AsyncMock(return_value=10),
        stack=MockStack(length=50),
        memory=MockMemory(),
        storage=MockStorage(),
        calldata=MockCalldata(),
        returndata=MockReturndata(),
        transient=MockTransient(),
        code=MockCode(),
    )

@pytest.fixture
def options(state) -> EvaluateOptions:
    return EvaluateOptions(
        variables = {
            "foo": Data.from_int(42),
            "bar": Data.from_hex("0x1f"),
        },
        regions = Regions((
            Region(
                name="stack",
                location="stack",
                slot=Data.from_int(42),
                offset=Data.from_int(0x60),
                length=Data.from_int(0x1f // 2),
            ),
            Region(
                name="memory",
                location="memory",
                slot=None,
                offset=Data.from_int(0x20 * 0x05),
                length=Data.from_int(42 - 0x1f),
            ),
        )),
        state = state,
    )

def uint(value: int) -> Literal:
    return Literal(root=EthdebugFormatDataValue(EthdebugFormatDataUnsigned(value)))

def hex(value: str) -> Literal:
    return Literal(root=EthdebugFormatDataValue(EthdebugFormatDataUnsigned(int(value, 16))))

def variable(name: str) -> Variable:
    return Variable(root=EthdebugFormatPointerIdentifier(name))

@pytest.mark.asyncio
async def test_evaluates_literal_expressions(options):
    assert await evaluate(uint(42), options) == Data.from_int(42)
    assert await evaluate(hex("0x1f"), options) == Data.from_hex("0x1f")

@pytest.mark.asyncio
async def test_evaluates_constant_expressions(options):
    assert await evaluate(Constant.field_wordsize, options) == Data.from_hex("0x20")

@pytest.mark.asyncio
async def test_evaluates_variable_expressions(options):
    assert await evaluate(variable("foo"), options) == Data.from_int(42)
    assert await evaluate(variable("bar"), options) == Data.from_hex("0x1f")

@pytest.mark.asyncio
async def test_evaluates_sum_expressions(options):
    expression = Arithmetic(**{"$sum": [42, "0x1f", "foo", "bar"]})
    assert await evaluate(expression, options) == Data.from_int(42 + 0x1f + 42 + 0x1f)

@pytest.mark.asyncio
async def test_evaluates_difference_expressions(options):
    expression = Arithmetic(**{"$difference": ["foo", "bar"]})
    assert await evaluate(expression, options) == Data.from_int(42 - 0x1f)

@pytest.mark.asyncio
async def test_evaluates_product_expressions(options):
    expression = Arithmetic(**{"$product": [42, "0x1f", "foo", "bar"]})
    assert await evaluate(expression, options) == Data.from_int(42 * 0x1f * 42 * 0x1f)

@pytest.mark.asyncio
async def test_evaluates_quotient_expressions(options):
    expression = Arithmetic(**{"$quotient": ["foo", "bar"]})
    assert await evaluate(expression, options) == Data.from_int(42 // 0x1f)

@pytest.mark.asyncio
async def test_evaluates_remainder_expressions(options):
    expression = Arithmetic(**{"$remainder": ["foo", "bar"]})
    assert await evaluate(expression, options) == Data.from_int(42 % 0x1f)

@pytest.mark.asyncio
async def test_evaluates_offset_lookup_expressions(options):
    expression = Lookup(**{".offset": "stack"})
    assert await evaluate(expression, options) == Data.from_int(0x60)

@pytest.mark.asyncio
async def test_evaluates_offset_lookup_expressions_with_this(options):
    expression = Lookup(**{".offset": "$this"})
    this_region = Region(
        name="$this",
        location="memory",
        slot=None,
        offset=Data.from_int(0x120),
        length=Data.from_int(0x40),
    )
    options.regions = options.regions.set_this(this_region)
    assert await evaluate(expression, options) == Data.from_int(0x120)

@pytest.mark.asyncio
async def test_evaluates_length_lookup_expressions(options):
    expression = Lookup(**{".length": "memory"})
    assert await evaluate(expression, options) == Data.from_int(11)

@pytest.mark.asyncio
async def test_evaluates_slot_lookup_expressions(options):
    expression = Lookup(**{".slot": "stack"})
    assert await evaluate(expression, options) == Data.from_int(42)

@pytest.mark.asyncio
async def test_evaluates_resize_expressions(options):
    data = await evaluate(Resize(**{"$sized1": 0}), options)
    assert len(data) == 1

    data = await evaluate(Resize(**{"$sized1": "0xabcd"}), options)
    assert len(data) == 1
    assert data == Data.from_int(0xcd)

    data = await evaluate(Resize(**{"$wordsized": "0xabcd"}), options)
    assert len(data) == 32
    assert data == Data.from_int(0xabcd).resize_to(32)

