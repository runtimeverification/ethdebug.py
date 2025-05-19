

from functools import singledispatch
from ethdebug import read
from ethdebug.cursor import Regions
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
    if isinstance(expression.root, int):
        return Data.from_int(expression.root)
    elif isinstance(expression.root, str):
        return Data.from_str(expression.root)
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
    data = options.variables.get(expression.root)
    if data is None:
        raise ValueError(f"Unknown variable: {expression.root}")
    return data

@evaluate.register
async def _(expression: Arithmetic, options: EvaluateOptions) -> Data:
   """
   Evaluate an arithmetic expression.
   """
   if expression.field_sum:
       return await evaluate_arithmetic_sum(expression, options)
   elif expression.field_difference:
       return await evaluate_arithmetic_difference(expression, options)
   elif expression.field_product:
       return await evaluate_arithmetic_product(expression, options)
   elif expression.field_quotient:
       return await evaluate_arithmetic_quotient(expression, options)
   elif expression.field_remainder:
       return await evaluate_arithmetic_remainder(expression, options)
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
    for expression in operands:
        sub = await evaluate(expression, options)
        result += sub.asUint()
        maxLength = max(maxLength, sub.length)
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
    for expression in operands:
        sub = await evaluate(expression, options)
        result *= sub.asUint()
        maxLength = max(maxLength, sub.length)
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
    if len(operands) != 2:
        raise ValueError("Difference operation requires exactly 2 operands")
    a = await evaluate(operands[0], options)
    b = await evaluate(operands[1], options)
    result = max(0, a.asUint() - b.asUint())
    return Data.from_int(result).pad_until_at_least(max(a.length, b.length))

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
    if len(operands) != 2:
        raise ValueError("Quotient operation requires exactly 2 operands")
    a = await evaluate(operands[0], options)
    b = await evaluate(operands[1], options)
    if b.asUint() == 0:
        raise ValueError("Division by zero")
    result = a.asUint() // b.asUint()
    return Data.from_int(result).pad_until_at_least(max(a.length, b.length))

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
    if len(operands) != 2:
        raise ValueError("Remainder operation requires exactly 2 operands")
    a = await evaluate(operands[0], options)
    b = await evaluate(operands[1], options)
    if b.asUint() == 0:
        raise ValueError("Division by zero")
    result = a.asUint() % b.asUint()
    return Data.from_int(result).pad_until_at_least(max(a.length, b.length))

@evaluate.register
async def _(expression: Resize, options: EvaluateOptions) -> Data:
    """
    Evaluate a resize expression.
    """
    # Iterate over all fields until we find $wordsized or $resize<N>
    for field in expression.root.keys():
        if field.startswith('$resize'):
            # $resize<N>
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
    elif resize_name.startswith('$resize'):
        # $resize<N>
        new_size = int(resize_name[len('$resize'):])
        if new_size <= 0:
            raise ValueError(f"Invalid resize size: {new_size}")
        
    # Evaluate the expression
    sub = expression.root[resize_name]
    result = await evaluate(sub, options)
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
        subs.append(await evaluate(operand, options))
    preimage = Data.zero().concat(subs)
    hash = Data.from_bytes(keccak(preimage))
    return hash

@evaluate.register
async def _(expression: Lookup, options: EvaluateOptions) -> Data:
    """
    Evaluate a lookup expression.
    """
    identifier : Literal['.slot', '.offset', '.length'] | None = None
    identifiers = ['.slot', '.offset', '.length']
    for field in expression.root.keys():
        if field in identifiers:
            identifier = field
            break
    if identifier is None:
        raise ValueError(f"Invalid lookup operation: {expression.root}")
    
    property = identifier.root[1:]
    
    region = options.regions.get(identifier)
    if region is None:
        raise ValueError(f"Regiond not found: {identifier}")
    
    data = region.get(property)

    if data is None:
        raise ValueError(f'Region named {identifier} does not have ${property} needed by lookup')
    return data

@evaluate.register
async def _(expression: Read, options: EvaluateOptions) -> Data:
    """
    Evaluate a read expression.
    """
    identifier = expression.field_read
    region = options.regions.get(identifier)
    if region is None:
        raise ValueError(f"Regiond not found: {identifier}")
    data = await read(region, options.state)
    return data