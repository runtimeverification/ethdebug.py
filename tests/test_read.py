import pytest
from unittest.mock import AsyncMock
from ethdebug.cursor import Region
from ethdebug.evaluate import EvaluateOptions
from ethdebug.machine import MachineState
from ethdebug.data import Data
from ethdebug.read import read

@pytest.fixture
def options() -> EvaluateOptions:
    state : MachineState = MockState(
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
    return MockOptions(
        state=state,
        regions=tuple(),
    )

@pytest.mark.asyncio
async def test_read_stack(options):
    region = MockRegion(location="stack", slot=Data.from_int(42), offset=Data.from_int(1), length=Data.from_int(2))
    result = await read(region, options.state)
    options.state.stack.read.assert_called_with(42, 1, 2)
    assert result == Data.from_bytes(bytearray([0x11, 0x22, 0x33, 0x44]))

@pytest.mark.asyncio
async def test_read_memory(options):
    region = MockRegion(location="memory", offset=Data.from_int(0), length=Data.from_int(4))
    result = await read(region, options.state)
    options.state.memory.read.assert_called_with(0, 4)
    assert result == Data.from_bytes(bytearray([0x55, 0x66, 0x77, 0x88]))

@pytest.mark.asyncio
async def test_read_storage(options):
    region = MockRegion(location="storage", slot=Data.from_int(0), offset=Data.from_int(2), length=Data.from_int(2))
    result = await read(region, options.state)
    options.state.storage.read.assert_called_with(0, 2, 2)
    assert result == Data.from_bytes(bytearray([0xaa, 0xbb, 0xcc, 0xdd]))

@pytest.mark.asyncio
async def test_read_calldata(options):
    region = MockRegion(location="calldata", offset=Data.from_int(0), length=Data.from_int(4))
    result = await read(region, options.state)
    options.state.calldata.read.assert_called_with(0, 4)
    assert result == Data.from_bytes(bytearray([0x11, 0x22, 0x33, 0x44]))

@pytest.mark.asyncio
async def test_read_returndata(options):
    region = MockRegion(location="returndata", offset=Data.from_int(0), length=Data.from_int(4))
    result = await read(region, options.state)
    options.state.returndata.read.assert_called_with(0, 4)
    assert result == Data.from_bytes(bytearray([0x55, 0x66, 0x77, 0x88]))

@pytest.mark.asyncio
async def test_read_transient(options):
    region = MockRegion(location="transient", slot=Data.from_int(42), offset=Data.from_int(1), length=Data.from_int(2))
    result = await read(region, options.state)
    options.state.transient.read.assert_called_with(42, 1, 2)
    assert result == Data.from_bytes(bytearray([0xaa, 0xbb, 0xcc, 0xdd]))

@pytest.mark.asyncio
async def test_read_code(options):
    region = MockRegion(location="code", offset=Data.from_int(0), length=Data.from_int(4))
    result = await read(region, options.state)
    options.state.code.read.assert_called_with(0, 4)
    assert result == Data.from_bytes(bytearray([0x11, 0x22, 0x33, 0x44]))

@pytest.mark.asyncio
async def test_default_stack_values(options):
    region = MockRegion(location="stack", slot=Data.from_int(42))
    result = await read(region, options.state)
    options.state.stack.read.assert_called_with(42, 0, 32)
    assert result == Data.from_bytes(bytearray([0x11, 0x22, 0x33, 0x44]))

@pytest.mark.asyncio
async def test_default_storage_values(options):
    region = MockRegion(location="storage", slot=Data.from_hex("0x1f"))
    result = await read(region, options.state)
    options.state.storage.read.assert_called_with(0x1f, 0, 32)
    assert result == Data.from_bytes(bytearray([0xaa, 0xbb, 0xcc, 0xdd]))

@pytest.mark.asyncio
async def test_default_transient_values(options):
    region = MockRegion(location="transient", slot=Data.from_int(42))
    result = await read(region, options.state)
    options.state.transient.read.assert_called_with(42, 0, 32)
    assert result == Data.from_bytes(bytearray([0xaa, 0xbb, 0xcc, 0xdd]))

class MockOptions:
    def __init__(self, state, regions):
        self.state = state
        self.regions = regions

class MockRegion(Region):
    def __init__(self, location, slot=None, offset=None, length=None):
        self.location = location
        self.slot = slot
        self.offset = offset
        self.length = length

class MockState(MachineState):
    def __init__(self, stack, memory, storage, calldata, returndata, transient, code):
        self.stack = stack
        self.memory = memory
        self.storage = storage
        self.calldata = calldata
        self.returndata = returndata
        self.transient = transient
        self.code = code

class MockStack:
    def __init__(self, length, read):
        self.length = length
        self.read = read

class MockMemory:
    def __init__(self, read):
        self.read = read

class MockStorage:
    def __init__(self, read):
        self.read = read

class MockCalldata:
    def __init__(self, read):
        self.read = read

class MockReturndata:
    def __init__(self, read):
        self.read = read

class MockTransient:
    def __init__(self, read):
        self.read = read

class MockCode:
    def __init__(self, read):
        self.read = read
    