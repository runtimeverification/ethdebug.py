from unittest.mock import AsyncMock
from ethdebug.data import Data
from ethdebug.machine import MachineState

class MockState(MachineState):
    def __init__(self, stack, memory, storage, calldata, returndata, transient, code, trace_index, program_counter, opcode):
        self.stack = stack
        self.memory = memory
        self.storage = storage
        self.calldata = calldata
        self.returndata = returndata
        self.transient = transient
        self.code = code
        self.trace_index = trace_index
        self.program_counter = program_counter
        self.opcode = opcode

class MockStack:
    def __init__(self, length, read = AsyncMock(return_value=Data.from_bytes(bytearray([0x11, 0x22, 0x33, 0x44])))):
        self.length = length
        self.read = read

class MockMemory:
    def __init__(self, read = AsyncMock(return_value=Data.from_bytes(bytearray([0x11, 0x22, 0x33, 0x44])))):
        self.read = read

class MockStorage:
    def __init__(self, read = AsyncMock(return_value=Data.from_bytes(bytearray([0x11, 0x22, 0x33, 0x44])))):
        self.read = read

class MockCalldata:
    def __init__(self, read = AsyncMock(return_value=Data.from_bytes(bytearray([0x11, 0x22, 0x33, 0x44])))):
        self.read = read

class MockReturndata:
    def __init__(self, read = AsyncMock(return_value=Data.from_bytes(bytearray([0x11, 0x22, 0x33, 0x44])))):
        self.read = read

class MockTransient:
    def __init__(self, read = AsyncMock(return_value=Data.from_bytes(bytearray([0x11, 0x22, 0x33, 0x44])))):
        self.read = read

class MockCode:
    def __init__(self, read = AsyncMock(return_value=Data.from_bytes(bytearray([0x11, 0x22, 0x33, 0x44])))):
        self.read = read
    