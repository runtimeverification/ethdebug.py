from __future__ import annotations

from typing import Union, Dict
from dataclasses import dataclass
from ethdebug.format.pointer_schema import Pointer
from ethdebug.cursor import Regions
from ethdebug.data import Data

@dataclass
class DereferencePointer:
    pointer: Pointer

@dataclass
class SaveRegions:
    regions: Regions

@dataclass
class SaveVariables:
    variables: Dict[str, Data]

# Union type for Memo
Memo = Union[DereferencePointer, SaveRegions, SaveVariables]