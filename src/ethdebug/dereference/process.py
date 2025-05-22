from functools import singledispatch
from typing import AsyncGenerator, Dict, List, Union
from dataclasses import dataclass, replace
from ethdebug.data import Data
from ethdebug.evaluate import EvaluateOptions, evaluate
from ethdebug.dereference.memo import DereferencePointer, Memo, SaveRegions, SaveVariables
from ethdebug.dereference.region import adjust_stack_length, evaluate_region
from ethdebug.format.pointer.collection.conditional_schema import EthdebugFormatPointerCollectionConditional
from ethdebug.format.pointer.collection.group_schema import EthdebugFormatPointerCollectionGroup
from ethdebug.format.pointer.collection.list_schema import EthdebugFormatPointerCollectionList
from ethdebug.format.pointer.collection.reference_schema import EthdebugFormatPointerCollectionReference
from ethdebug.format.pointer.collection.scope_schema import EthdebugFormatPointerCollectionScope
from ethdebug.format.pointer.region_schema import EthdebugFormatPointerRegion
from ethdebug.format.pointer.template_schema import EthdebugFormatPointerTemplate
from ethdebug.format.pointer_schema import EthdebugFormatPointer
from ethdebug.machine import MachineState
from ethdebug.dereference.cursor import Region, Regions

@dataclass
class ProcessState:
    templates: Dict[str, EthdebugFormatPointerTemplate]
    state: MachineState
    stack_length_change: int
    regions: Regions
    variables: Dict[str, Data]


Process = AsyncGenerator[Region | Memo]


@singledispatch
async def process_pointer(pointer: EthdebugFormatPointer, state: ProcessState) -> Process:
    raise TypeError(f"Unexpected pointer type: {type(pointer)}")
    yield None # <- If the function does not contain a yield statement, it will not be a generator function


@process_pointer.register(EthdebugFormatPointerRegion)
async def process_region(region: EthdebugFormatPointerRegion, state: ProcessState) -> Process:
    adjusted = adjust_stack_length(region, state.stack_length_change)
    evaluated_region = await evaluate_region(
        adjusted,
        EvaluateOptions(
            state=state.state,
            regions=state.regions,
            variables=state.variables
        )
    )

    yield evaluated_region

    if region.root.name is not None:
        yield SaveRegions(Regions((evaluated_region,)))

@process_pointer.register(EthdebugFormatPointerCollectionGroup)
async def process_group(collection: EthdebugFormatPointerCollectionGroup, options: ProcessState) -> Process:
    for pointer in collection.group: 
        yield DereferencePointer(pointer)

@process_pointer.register(EthdebugFormatPointerCollectionList)
async def process_list(collection: EthdebugFormatPointerCollectionList, options: ProcessState) -> Process:
    count = (await evaluate(collection.list.count.root, options)).as_uint()
    
    for index in range(count):
        yield SaveVariables({
            collection.list.each.root: Data.from_int(index)
        })
        yield DereferencePointer(collection.list.is_)

@process_pointer.register(EthdebugFormatPointerCollectionConditional)
async def process_conditional(collection: EthdebugFormatPointerCollectionConditional, options: ProcessState) -> Process:
    condition = (await evaluate(collection.if_.root, options)).as_uint()

    if condition:
        yield DereferencePointer(collection.then)
        return
    
    if collection.else_ is not None:
        yield DereferencePointer(collection.else_)

@process_pointer.register(EthdebugFormatPointerCollectionScope)
async def process_scope(collection: EthdebugFormatPointerCollectionScope, options: ProcessState) -> Process:
    all_variables = options.variables.copy()
    new_variables = {}

    for identifier, expression in collection.define.items():
        data = await evaluate(expression.root, replace(options, variables= all_variables))
        all_variables[identifier] = data
        new_variables[identifier] = data

    yield SaveVariables(new_variables)
    yield DereferencePointer(collection.in_)

@process_pointer.register(EthdebugFormatPointerCollectionReference)
async def process_reference(collection: EthdebugFormatPointerCollectionReference, options: ProcessState) -> Process:
    template_name = collection.template
    template = options.templates.get(template_name.root)

    if not template:
        raise ValueError(f"Unknown pointer template named {template_name}")

    missing_variables = [
        identifier for identifier in template.expect
        if identifier not in options.variables
    ]

    if missing_variables:
        raise ValueError(
            f"Invalid reference to template named {template_name}; missing expected "
            f"variables with identifiers: {', '.join(str(v) for v in missing_variables)}. "
            f"Please ensure these variables are defined prior to this reference."
        )

    yield DereferencePointer(template.for_)