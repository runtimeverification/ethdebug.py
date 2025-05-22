from functools import singledispatch
from typing import TypeVar, Union
from ethdebug.format.pointer.expression_schema import Arithmetic, EthdebugFormatPointerExpression, Literal
from ethdebug.dereference.cursor import Region
from ethdebug.data import Data
from ethdebug.evaluate import evaluate, EvaluateOptions
from ethdebug.format.pointer.region.stack_schema import EthdebugFormatPointerRegionStack
from ethdebug.format.pointer.region_schema import EthdebugFormatPointerRegion
from dataclasses import replace

class CircularReferenceError(Exception):
    pass

async def evaluate_region(
    region: EthdebugFormatPointerRegion,
    options: EvaluateOptions
) -> Region:
    """
    Evaluate all PointerExpression-value properties on a given region.

    Due to the availability of `$this` as a builtin allowable by the schema,
    this function evaluates components using a fixed-point iteration algorithm.
    In each iteration, we try to evaluate the `offset`, `length`, and `slot` properties.
    If the region did no change after an iteration, we reached a fixed point and the algorithm terminates.
    There are two kinds of fixed points:
    1. The region is fully evaluated, meaning all properties are set to a value.
    2. The region is not fully evaluated, but the properties are not changing anymore. This indicates a circular reference.

    If at the end of the algorithm, the region is still not fully evaluated,
    a `CircularReferenceError` is raised.
    """
    slot = getattr(region.root, "slot", None)

    this_region = Region(
        name="$this",
        location=region.root.location,
        slot=slot,
        offset=region.root.offset,
        length=region.root.length
    )
    first_itereation = True
    
    while first_itereation or not is_fixed_point(last_region, this_region):
        first_itereation = False
        last_region = this_region
        try:
            if isinstance(this_region.offset, EthdebugFormatPointerExpression):
                data = await evaluate(this_region.offset, options=options.set_this(this_region))
                this_region = replace(this_region, offset=data)
            if isinstance(this_region.length, EthdebugFormatPointerExpression):
                data = await evaluate(this_region.length.root, options=options.set_this(this_region))
                this_region = replace(this_region, length=data)
            if isinstance(this_region.slot, EthdebugFormatPointerExpression):
                data = await evaluate(this_region.slot.root, options=options.set_this(this_region))
                this_region = replace(this_region, slot=data)
        except KeyError as e:
            ...
    if not is_fully_evaluated(this_region):
        raise CircularReferenceError(
            f"Region {getattr(region.root, 'name', '<unnamed>')} could not be fully evaluated. "
        )

    result = replace(this_region, name=getattr(region.root, "name", None))
    return result

def is_fully_evaluated(region: Region) -> bool:
    """
    Returns True if all properties of the region are evaluated to a value.
    """
    return region.slot is None or isinstance(region.slot, Data) and \
        region.offset is None or isinstance(region.offset, Data) and \
        region.length is None or isinstance(region.length, Data)

def is_fixed_point(a: Region, b: Region) -> bool:
    """
    Returns True if both regions are evaluated to the same degree.
    """
    return type(a.slot) == type(b.slot) and \
        type(a.offset) == type(b.offset) and \
        type(a.length) == type(b.length)

def adjust_stack_length(
  region: EthdebugFormatPointerExpression,
  stack_length_change: int
) -> EthdebugFormatPointerRegion:
    if stack_length_change == 0:
        slot = region.slot
    elif stack_length_change > 0:
        slot = Arithmetic(field_sum=[region.slot, Literal(stack_length_change)])
    else:
        slot = Arithmetic(field_difference=[region.slot, Literal(stack_length_change)])
    return EthdebugFormatPointerRegion(
        location=region.location,
        name=region.name,
        slot=slot,
        offset=region.offset,
        length=region.length
    )