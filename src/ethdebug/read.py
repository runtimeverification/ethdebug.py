from typing import Optional, Dict, Any, Union
from dataclasses import dataclass

@dataclass
class ReadOptions:
    state: 'MachineState'

class MachineState:
    def __init__(self, stack, memory, storage, calldata, returndata, transient, code):
        self.stack = stack
        self.memory = memory
        self.storage = storage
        self.calldata = calldata
        self.returndata = returndata
        self.transient = transient
        self.code = code

class CursorRegion:
    def __init__(self, location, **kwargs):
        self.location = location
        self.properties = kwargs

    def get_property(self, key: str) -> Optional['Data']:
        return self.properties.get(key)

class Data:
    def __init__(self, value):
        self.value = value

    def as_uint(self) -> int:
        return int(self.value)

async def read(region: CursorRegion, options: ReadOptions) -> 'Data':
    location = region.location
    state = options.state

    if location == "stack":
        slot = with_properties_as_uints(["slot"], region).get("slot", 0)
        offset = with_properties_as_uints(["offset"], region).get("offset", 0)
        length = with_properties_as_uints(["length"], region).get("length", 32)
        return await state.stack.peek(depth=slot, slice={"offset": offset, "length": length})

    elif location == "memory":
        offset = with_properties_as_uints(["offset"], region).get("offset", 0)
        length = with_properties_as_uints(["length"], region).get("length", 32)
        return await state.memory.read(slice={"offset": offset, "length": length})

    elif location == "storage":
        slot = with_properties_as_uints(["slot"], region).get("slot", 0)
        offset = with_properties_as_uints(["offset"], region).get("offset", 0)
        length = with_properties_as_uints(["length"], region).get("length", 32)
        return await state.storage.read(slot=slot, slice={"offset": offset, "length": length})

    elif location == "calldata":
        offset = with_properties_as_uints(["offset"], region).get("offset", 0)
        length = with_properties_as_uints(["length"], region).get("length", 32)
        return await state.calldata.read(slice={"offset": offset, "length": length})

    elif location == "returndata":
        offset = with_properties_as_uints(["offset"], region).get("offset", 0)
        length = with_properties_as_uints(["length"], region).get("length", 32)
        return await state.returndata.read(slice={"offset": offset, "length": length})

    elif location == "transient":
        slot = with_properties_as_uints(["slot"], region).get("slot", 0)
        offset = with_properties_as_uints(["offset"], region).get("offset", 0)
        length = with_properties_as_uints(["length"], region).get("length", 32)
        return await state.transient.read(slot=slot, slice={"offset": offset, "length": length})

    elif location == "code":
        offset = with_properties_as_uints(["offset"], region).get("offset", 0)
        length = with_properties_as_uints(["length"], region).get("length", 32)
        return await state.code.read(slice={"offset": offset, "length": length})

def with_properties_as_uints(keys: list, region: CursorRegion) -> Dict[str, Union[int, None]]:
    result = {}
    for key in keys:
        data = region.get_property(key)
        if data is not None:
            result[key] = data.as_uint()
    return result
