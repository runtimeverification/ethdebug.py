

from functools import singledispatch
import typing
from ethdebug import read
from ethdebug.cursor import Region, Regions
from ethdebug.data import Data
from ethdebug.format.pointer.expression_schema import Arithmetic, Constant, EthdebugFormatPointerExpression, Keccak256, Literal, Lookup, Operands, Read, Resize, Variable
from ethdebug.machine import MachineState
from eth_hash.auto import keccak

class EvaluateOptions:
    state: MachineState
    regions: Regions
    variables: dict[str, Data]

@singledispatch
async def evaluate(
    expression: EthdebugFormatPointerExpression,
    options: EvaluateOptions,
) -> Data:
    raise ValueError("Unsupported expression type")

@evaluate.register
async def _(expression: Literal, options: EvaluateOptions) -> Data:
    """
    Evaluate a literal expression.
    """
    unwraped : int | str = expression.root.root.root
    if isinstance(unwraped, int):
        return Data.from_int(unwraped)
    elif isinstance(unwraped, str):
        return Data.from_hex(unwraped)
    else:
        raise ValueError(f"Unsupported literal type: {type(expression.root)}")
    
@evaluate.register
async def _(expression: Constant, options: EvaluateOptions) -> Data:
    """
    Evaluate a constant expression.
    """
    if expression == Constant.field_wordsize:
        return Data.from_int(32)
    raise ValueError(f"Unsupported constant: {expression.root}")

@evaluate.register
async def _(expression: Variable, options: EvaluateOptions) -> Data:
    """
    Evaluate a variable expression.
    """
    data = options.variables.get(expression.root.root)
    if data is None:
        raise ValueError(f"Unknown variable: {expression.root.root}")
    return data

@evaluate.register
async def _(expression: Arithmetic, options: EvaluateOptions) -> Data:
   """
   Evaluate an arithmetic expression.
   """
   if expression.field_sum:
       return await evaluate_arithmetic_sum(expression.field_sum, options)
   elif expression.field_difference:
       return await evaluate_arithmetic_difference(expression.field_difference, options)
   elif expression.field_product:
       return await evaluate_arithmetic_product(expression.field_product, options)
   elif expression.field_quotient:
       return await evaluate_arithmetic_quotient(expression.field_quotient, options)
   elif expression.field_remainder:
       return await evaluate_arithmetic_remainder(expression.field_remainder, options)
   else:
       raise ValueError(f"Unsupported arithmetic operation: {expression}")

async def evaluate_arithmetic_sum(
  operands: Operands,
  options: EvaluateOptions
) -> Data:
    """
    Evaluate an arithmetic sum expression.
    Operands are evaluated left-to-right.
    Defaults to 0 if no operands are provided.
    The result is padded to the maximum length of the operands.
    """
    result = 0
    maxLength = 0
    for expression in operands.root:
        sub = await evaluate(expression.root, options)
        result += sub.as_uint()
        maxLength = max(maxLength, len(sub))
    return Data.from_int(result).pad_until_at_least(maxLength)

async def evaluate_arithmetic_product(
  operands: Operands,
  options: EvaluateOptions
) -> Data:
    """
    Evaluate an arithmetic product expression.
    Operands are evaluated left-to-right.
    Defaults to 1 if no operands are provided.
    The result is padded to the maximum length of the operands.
    """
    result = 1
    maxLength = 0
    for expression in operands.root:
        sub = await evaluate(expression.root, options)
        result *= sub.as_uint()
        maxLength = max(maxLength, len(sub))
    return Data.from_int(result).pad_until_at_least(maxLength)

async def evaluate_arithmetic_difference(
    operands: Operands,
    options: EvaluateOptions
) -> Data:
    """
    Evaluate an arithmetic difference expression.
    Operands are evaluated left-to-right.
    The result is padded to the maximum length of the operands.
    Raises an exception if number of operands is not 2.
    This method operates on unsigned integers.
    The result is bounded to 0 if the second operand is larger than the first.
    """
    if len(operands.root) != 2:
        raise ValueError("Difference operation requires exactly 2 operands")
    a = await evaluate(operands.root[0].root, options)
    b = await evaluate(operands.root[1].root, options)
    result = max(0, a.as_uint() - b.as_uint())
    return Data.from_int(result).pad_until_at_least(max(len(a), len(b)))

async def evaluate_arithmetic_quotient(
    operands: Operands,
    options: EvaluateOptions
) -> Data:
    """
    Evaluate an arithmetic quotient expression.
    Operands are evaluated left-to-right.
    The result is padded to the maximum length of the operands.
    Raises an exception if number of operands is not 2.
    Raises an exception if the second operand is 0.
    This method operates on unsigned integers.
    """
    if len(operands.root) != 2:
        raise ValueError("Quotient operation requires exactly 2 operands")
    a = await evaluate(operands.root[0].root, options)
    b = await evaluate(operands.root[1].root, options)
    if b.as_uint() == 0:
        raise ValueError("Division by zero")
    result = a.as_uint() // b.as_uint()
    return Data.from_int(result).pad_until_at_least(max(len(a), len(b)))

async def evaluate_arithmetic_remainder(
    operands: Operands,
    options: EvaluateOptions
) -> Data:
    """
    Evaluate an arithmetic remainder expression.
    Operands are evaluated left-to-right.
    The result is padded to the maximum length of the operands.
    Raises an exception if number of operands is not 2.
    Raises an exception if the second operand is 0.
    This method operates on unsigned integers.
    """
    if len(operands.root) != 2:
        raise ValueError("Remainder operation requires exactly 2 operands")
    a = await evaluate(operands.root[0].root, options)
    b = await evaluate(operands.root[1].root, options)
    if b.as_uint() == 0:
        raise ValueError("Division by zero")
    result = a.as_uint() % b.as_uint()
    return Data.from_int(result).pad_until_at_least(max(len(a), len(b)))

@evaluate.register
async def _(expression: Resize, options: EvaluateOptions) -> Data:
    """
    Evaluate a resize expression.
    """
    # Iterate over all fields until we find $wordsized or $sized<N>
    for field in expression.root.keys():
        if field.startswith('$sized'):
            # $sized<N>
            resize_name = field
            break
        elif field == '$wordsized':
            # $wordsized
            resize_name = field
            break

    new_size = 0
    if resize_name == '$wordsized':
        # $wordsized
        new_size = 32
    elif resize_name.startswith('$sized'):
        # $sized<N>
        new_size = int(resize_name[len('$sized'):])
        if new_size <= 0:
            raise ValueError(f"Invalid resize size: {new_size}")
        
    # Evaluate the expression
    sub = expression.root[resize_name]
    result = await evaluate(sub.root, options)
    # Resize the result
    return result.resize_to(new_size)

@evaluate.register
async def _(expression: Keccak256, options: EvaluateOptions) -> Data:
    """
    Evaluate a keccack256 expression.
    """
    # Concatenate all the operands
    subs = []
    for operand in expression.root:
        subs.append(await evaluate(operand.root, options))
    preimage = Data.zero().concat(subs)
    hash = Data.from_bytes(keccak(preimage))
    return hash

@evaluate.register
async def _(expression: Lookup, options: EvaluateOptions) -> Data:
    """
    Evaluate a lookup expression.
    """
    property : Literal['.slot', '.offset', '.length'] | None = None
    property_names = ['.slot', '.offset', '.length']
    for field in expression.root.keys():
        if field in property_names:
            property = field
            break
    if property is None:
        raise ValueError(f"Invalid lookup operation: {expression.root}")
    
    reference = expression.root.get(property)
    
    region = options.regions.lookup(reference.root)
    if region is None:
        raise ValueError(f"Regiond not found: {reference.root}")
    
    data = region_lookup(property, region)

    if data is None:
        raise ValueError(f'Region named {reference.root} does not have ${property} needed by lookup')
    return data

@evaluate.register
async def _(expression: Read, options: EvaluateOptions) -> Data:
    """
    Evaluate a read expression.
    """
    identifier = expression.field_read
    region = options.regions.lookup(identifier)
    if region is None:
        raise ValueError(f"Regiond not found: {identifier}")
    data = await read(region, options.state)
    return data


def region_lookup(
    property: typing.Literal['.slot', '.offset', '.length'],
    region: Region
) -> Data:
    if property == '.slot':
        return region.slot
    elif property == '.offset':
        return region.offset
    elif property == '.length':
        return region.length
    else:
        raise ValueError(f"Invalid property: {property}")