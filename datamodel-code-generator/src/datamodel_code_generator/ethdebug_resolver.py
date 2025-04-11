from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

def ethdebug_get_body(
    base_path: Path,
    url: str
) -> str:
    file_name = url[len('schema:ethdebug/format/'):] + '.schema.yaml'
    schema_file = base_path / file_name
    return schema_file.read_text(encoding="utf-8")


def ethdebug_join_url(url: str, ref: str = ".") -> str:
    return ref
