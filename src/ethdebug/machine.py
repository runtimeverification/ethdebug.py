from __future__ import annotations
from typing import AsyncIterable, Protocol

from ethdebug.data import Data

class Machine(Protocol):
    async def trace(self) -> MachineTrace:
        ...

class MachineTrace(Protocol):

    def __aiter__(self) -> AsyncIterable[MachineState]:
        ...

class MachineState(Protocol):
    async def trace_index(self) -> int:
        ...

    async def program_counter(self) -> int:
        ...

    async def opcode(self) -> str:
        ...

    def stack(self) -> MachineStack:
        ...

    def memory(self) -> MachineMemory:
        ...

    def storage(self) -> MachineStorage:
        ...

    def calldata(self) -> MachineCalldata:
        ...

    def returndata(self) -> MachineReturndata:
        ...

    def transient(self) -> MachineTransientStorage:
        ...

    def code(self) -> MachineCode:
        ...
    

class MachineStack(Protocol):
    async def length(self) -> int:
        ...

    async def read(self, slot: int, offset: int, length: int = 32) -> Data:
        ...


class MachineMemory(Protocol):
    async def length(self) -> int:
        ...

    async def read(self, ofset: int, length: int = 32) -> Data:
        ...

class MachineReturndata(Protocol):
    async def length(self) -> int:
        ...

    async def read(self, ofset: int, length: int = 32) -> Data:
        ...

class MachineCalldata(Protocol):
    async def length(self) -> int:
        ...

    async def read(self, ofset: int, length: int = 32) -> Data:
        ...

class MachineStorage(Protocol):
    async def read(self, slot: int, offset: int, length: int = 32) -> Data:
        ...

class MachineTransientStorage(Protocol):
    async def read(self, slot: int, offset: int, length: int = 32) -> Data:
        ...

class MachineCode(Protocol):
    async def length(self) -> int:
        ...

    async def read(self, ofset: int, length: int = 32) -> Data:
        ...