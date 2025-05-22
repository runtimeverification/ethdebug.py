from dataclasses import dataclass, replace
from typing import  AsyncIterable, Dict
from ethdebug.format.pointer_schema import EthdebugFormatPointer
from ethdebug.format.pointer.template_schema import EthdebugFormatPointerTemplate
from ethdebug.machine import MachineState
from ethdebug.dereference.cursor import Cursor, Region
from ethdebug.dereference.generate import generate_regions, GenerateRegionsOptions

@dataclass
class DereferenceOptions:
    """
    Options for dereferencing a pointer.
    """
    state: MachineState
    templates: Dict[str, EthdebugFormatPointerTemplate]

async def dereference(pointer: EthdebugFormatPointer, dereference_options: DereferenceOptions) -> Cursor:
    """
    Dereference a pointer into a Cursor object, allowing inspection of machine state.

    :param pointer: The pointer to dereference.
    :param dereference_options: Options for dereferencing.
    :return: A Cursor object.
    """
    dereference_options = dereference_options
    options = await initialize_generate_regions_options(dereference_options)

    def simple_cursor(state: MachineState) -> AsyncIterable[Region]:
        async def async_generator():
            async for region in generate_regions(pointer, replace(options, state=state)):
                yield region
        return async_generator()
    return Cursor(simple_cursor)

async def initialize_generate_regions_options(dereference_options: DereferenceOptions) -> GenerateRegionsOptions:
    """
    Convert DereferenceOptions into the specific pieces of information needed by `generate_regions`.

    :param dereference_options: The dereference options.
    :return: A dictionary of options for `generate_regions`.
    """
    initial_stack_length = 0
    if dereference_options.state:
        initial_stack_length = await dereference_options.state.stack.length

    return GenerateRegionsOptions(
        templates= dereference_options.templates,
        initial_stack_length= initial_stack_length,
        state= dereference_options.state,
    )