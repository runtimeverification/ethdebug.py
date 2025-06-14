# generated by datamodel-codegen:
#   filename:  type/wrapper.schema.yaml

from __future__ import annotations

from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel, Field, RootModel


class TypeWrapper(BaseModel):
    type: Any


class Array(RootModel[List[TypeWrapper]]):
    root: Annotated[
        List[TypeWrapper],
        Field(
            description='A list of wrapped types, where the wrapper may add fields',
            title='{ "type": ... }[]',
        ),
    ]


class Object(RootModel[Optional[Dict[str, TypeWrapper]]]):
    root: Optional[Dict[str, TypeWrapper]] = None
