# generated by datamodel-codegen:
#   filename:  info.schema.yaml

from __future__ import annotations

from typing import List

from pydantic import BaseModel

from .materials.compilation_schema import MaterialsCompilation
from .program_schema import Program


class Info(BaseModel):
    programs: List[Program]
    compilation: MaterialsCompilation
