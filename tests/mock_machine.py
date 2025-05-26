from unittest.mock import AsyncMock
from ethdebug.data import Data
from ethdebug.machine import MachineState
from dataclasses import dataclass

@dataclass
class MockState(MachineState):
    stack: 'MockStack'
    memory: 'MockMemory'
    storage: 'MockStorage'
    calldata: 'MockCalldata'
    returndata: 'MockReturndata'
    transient: 'MockTransient'
    code: 'MockCode'
    trace_index: int
    program_counter: int
    opcode: str

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
    