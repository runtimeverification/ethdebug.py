from typing import AsyncIterable, Dict, List
from dataclasses import dataclass, replace
from ethdebug.dereference.cursor import Regions, Region
from ethdebug.format.pointer.template_schema import EthdebugFormatPointerTemplate
from ethdebug.format.pointer_schema import EthdebugFormatPointer
from ethdebug.machine import MachineState
from ethdebug.data import Data
from .memo import DereferencePointer, Memo, SaveRegions, SaveVariables
from .process import process_pointer, ProcessState

@dataclass
class GenerateRegionsOptions:
    templates: Dict[str, EthdebugFormatPointerTemplate]
    state: MachineState
    initial_stack_length: int

async def generate_regions(
    pointer: EthdebugFormatPointer,
    options: GenerateRegionsOptions
) -> AsyncIterable[Region]:
    process_options = await initialize_process_state(options)

    # Extract records for mutation
    regions = process_options.regions
    variables = process_options.variables

    stack: List[Memo] = [DereferencePointer(pointer)]
    while stack:
        memo = stack.pop()

        memos: List[Memo] = []
        if isinstance(memo, DereferencePointer):
            async for region in process_pointer(memo.pointer, options):
                if isinstance(region, Region):
                    yield region
                else:
                    memos.append(region)
        elif isinstance(memo, SaveRegions):
            regions = replace(regions, regions=memo.regions)
        elif isinstance(memo, SaveVariables):
            variables.update(memo.variables)

        # Add new memos to the stack in reverse order
        stack.extend(reversed(memos))


async def initialize_process_state(
    options: GenerateRegionsOptions
) -> ProcessState:
    current_stack_length = await options.state.stack.length()
    stack_length_change = current_stack_length - options.initial_stack_length

    regions: Regions = Regions(())
    variables: Dict[str, Data] = {}

    return ProcessState(
        templates=options.templates,
        state=options.state,
        stack_length_change=stack_length_change,
        regions=regions,
        variables=variables,
    )