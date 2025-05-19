from ethdebug.cursor import Region
from ethdebug.data import Data
from ethdebug.machine import MachineState


async def read(region: Region, state: MachineState) -> Data:
    location = region.location

    slot = region.slot.as_uint() if region.slot else 0
    offset = region.offset.as_uint() if region.offset else 0
    length = region.length.as_uint() if region.length else 32

    if location == "stack":
        return await state.stack.read(slot, offset, length)
    elif location == "memory":
        return await state.memory.read(offset, length)
    elif location == "storage":
        return await state.storage.read(offset, length)
    elif location == "calldata":
        return await state.calldata.read(offset, length)
    elif location == "returndata":
        return await state.returndata.read(offset, length)
    elif location == "transient":
        return await state.transient.read(slot, offset, length)
    elif location == "code":
        return await state.code.read(slot, offset, length)
