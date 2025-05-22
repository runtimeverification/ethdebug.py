import pytest
from unittest.mock import AsyncMock
from ethdebug.cursor import Region
from ethdebug.machine import MachineState
from ethdebug.data import Data
from ethdebug.read import read
from tests.mock_machine import MockCalldata, MockCode, MockMemory, MockReturndata, MockStack, MockState, MockStorage, MockTransient

@pytest.fixture
def state() -> MachineState:
    state : MachineState = MockState(
        trace_index=42,
        opcode="PUSH1",
        program_counter=10,
        stack = MockStack(
            length = 50,
            read = AsyncMock(return_value=Data.from_bytes(bytearray([0x11, 0x22, 0x33, 0x44]))),
        ),
        memory = MockMemory(
            read = AsyncMock(return_value=Data.from_bytes(bytearray([0x55, 0x66, 0x77, 0x88]))),
        ),
        storage = MockStorage(
            read = AsyncMock(return_value=Data.from_bytes(bytearray([0xaa, 0xbb, 0xcc, 0xdd]))),
        ),
        calldata = MockCalldata(
            read = AsyncMock(return_value=Data.from_bytes(bytearray([0x11, 0x22, 0x33, 0x44]))),
        ),
        returndata = MockReturndata(
            read = AsyncMock(return_value=Data.from_bytes(bytearray([0x55, 0x66, 0x77, 0x88]))),
        ),
        transient = MockTransient(
            read = AsyncMock(return_value=Data.from_bytes(bytearray([0xaa, 0xbb, 0xcc, 0xdd]))),
        ),
        code = MockCode(
            read = AsyncMock(return_value=Data.from_bytes(bytearray([0x11, 0x22, 0x33, 0x44]))),
        ),
    )
    return state

@pytest.mark.asyncio
async def test_read_stack(state):
    region = MockRegion(location="stack", slot=Data.from_int(42), offset=Data.from_int(1), length=Data.from_int(2))
    result = await read(region, state)
    state.stack.read.assert_called_with(42, 1, 2)
    assert result == Data.from_bytes(bytearray([0x11, 0x22, 0x33, 0x44]))

@pytest.mark.asyncio
async def test_read_memory(state):
    region = MockRegion(location="memory", offset=Data.from_int(0), length=Data.from_int(4))
    result = await read(region, state)
    state.memory.read.assert_called_with(0, 4)
    assert result == Data.from_bytes(bytearray([0x55, 0x66, 0x77, 0x88]))

@pytest.mark.asyncio
async def test_read_storage(state):
    region = MockRegion(location="storage", slot=Data.from_int(0), offset=Data.from_int(2), length=Data.from_int(2))
    result = await read(region, state)
    state.storage.read.assert_called_with(0, 2, 2)
    assert result == Data.from_bytes(bytearray([0xaa, 0xbb, 0xcc, 0xdd]))

@pytest.mark.asyncio
async def test_read_calldata(state):
    region = MockRegion(location="calldata", offset=Data.from_int(0), length=Data.from_int(4))
    result = await read(region, state)
    state.calldata.read.assert_called_with(0, 4)
    assert result == Data.from_bytes(bytearray([0x11, 0x22, 0x33, 0x44]))

@pytest.mark.asyncio
async def test_read_returndata(state):
    region = MockRegion(location="returndata", offset=Data.from_int(0), length=Data.from_int(4))
    result = await read(region, state)
    state.returndata.read.assert_called_with(0, 4)
    assert result == Data.from_bytes(bytearray([0x55, 0x66, 0x77, 0x88]))

@pytest.mark.asyncio
async def test_read_transient(state):
    region = MockRegion(location="transient", slot=Data.from_int(42), offset=Data.from_int(1), length=Data.from_int(2))
    result = await read(region, state)
    state.transient.read.assert_called_with(42, 1, 2)
    assert result == Data.from_bytes(bytearray([0xaa, 0xbb, 0xcc, 0xdd]))

@pytest.mark.asyncio
async def test_read_code(state):
    region = MockRegion(location="code", offset=Data.from_int(0), length=Data.from_int(4))
    result = await read(region, state)
    state.code.read.assert_called_with(0, 4)
    assert result == Data.from_bytes(bytearray([0x11, 0x22, 0x33, 0x44]))

@pytest.mark.asyncio
async def test_default_stack_values(state):
    region = MockRegion(location="stack", slot=Data.from_int(42))
    result = await read(region, state)
    state.stack.read.assert_called_with(42, 0, 32)
    assert result == Data.from_bytes(bytearray([0x11, 0x22, 0x33, 0x44]))

@pytest.mark.asyncio
async def test_default_storage_values(state):
    region = MockRegion(location="storage", slot=Data.from_hex("0x1f"))
    result = await read(region, state)
    state.storage.read.assert_called_with(0x1f, 0, 32)
    assert result == Data.from_bytes(bytearray([0xaa, 0xbb, 0xcc, 0xdd]))

@pytest.mark.asyncio
async def test_default_transient_values(state):
    region = MockRegion(location="transient", slot=Data.from_int(42))
    result = await read(region, state)
    state.transient.read.assert_called_with(42, 0, 32)
    assert result == Data.from_bytes(bytearray([0xaa, 0xbb, 0xcc, 0xdd]))

class MockRegion(Region):
    def __init__(self, location, slot=None, offset=None, length=None):
        self.location = location
        self.slot = slot
        self.offset = offset
        self.length = length
