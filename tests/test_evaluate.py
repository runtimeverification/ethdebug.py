import pytest
from unittest.mock import AsyncMock
from ethdebug.evaluate import EvaluateOptions, evaluate
from ethdebug.data import Data
from ethdebug.cursor import Region, Regions
from ethdebug.format.pointer.expression_schema import Arithmetic, Constant, Literal, Lookup, Resize, Variable
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
    return MockOptions(
        variables = {
            "foo": Data.from_int(42),
            "bar": Data.from_hex("0x1f"),
        },
        regions = Regions((
            MockRegion(
                name="stack",
                location="stack",
                slot=Data.from_int(42),
                offset=Data.from_int(0x60),
                length=Data.from_int(0x1f // 2),
            ),
            MockRegion(
                name="memory",
                location="memory",
                offset=Data.from_int(0x20 * 0x05),
                length=Data.from_int(42 - 0x1f),
            ),
        )),
        state = state,
    )

@pytest.mark.asyncio
async def test_evaluates_literal_expressions(options):
    assert await evaluate(Literal(42), options) == Data.from_int(42)
    assert await evaluate(Literal("0x1f"), options) == Data.from_hex("0x1f")

@pytest.mark.asyncio
async def test_evaluates_constant_expressions(options):
    assert await evaluate(Constant.field_wordsize, options) == Data.from_hex("0x20")

@pytest.mark.asyncio
async def test_evaluates_variable_expressions(options):
    assert await evaluate(Variable("foo"), options) == Data.from_int(42)
    assert await evaluate(Variable("bar"), options) == Data.from_hex("0x1f")

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
    this_region = MockRegion(
        name="$this",
        location="memory",
        offset=Data.from_int(0x120),
        length=Data.from_int(0x40),
    )
    options.regions = Regions((this_region,))
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


class MockOptions:
    def __init__(self, state, regions, variables):
        self.state = state
        self.regions = regions
        self.variables = variables

class MockRegion(Region):
    def __init__(self, name, location, slot=None, offset=None, length=None):
        self.name = name
        self.location = location
        self.slot = slot
        self.offset = offset
        self.length = length
