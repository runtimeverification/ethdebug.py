from __future__ import annotations
from abc import ABC
from typing import AsyncIterable, Protocol, runtime_checkable, Optional

from ethdebug.data import Data

@runtime_checkable
class Machine(Protocol):
    async def trace(self) -> AsyncIterable["Machine.State"]:
        ...


class MachineState(ABC):
    async def trace_index(self) -> int:
        ...

    async def program_counter(self) -> int:
        ...

    async def opcode(self) -> str:
        ...

    def stack(self) -> MachineStateStack:
        ...

    def memory(self) -> MachineStateBytes:
        ...

    def storage(self) -> MachineStateWords:
        ...

    def calldata(self) -> MachineStateBytes:
        ...

    def returndata(self) -> MachineStateBytes:
        ...

    def transient(self) -> MachineStateWords:
        ...

    def code(self) -> MachineStateBytes:
        ...


class MachineStateSlice:
    def __init__(self, offset: int, length: int):
        self.offset = offset
        self.length = length


class MachineStateStack:
    async def length(self) -> int:
        ...

    async def peek(self, depth: int, slice: Optional[MachineStateSlice] = None) -> Data:
        ...


class MachineStateBytes:
    async def length(self) -> int:
        ...

    async def read(self, slice: MachineStateSlice) -> Data:
        ...


class MachineStateWords:
    async def read(self, slot: Data, slice: Optional[MachineStateSlice] = None) -> Data:
        ...
