"""
bytecode.py

EVM bytecode and solc source-map decoders.
"""

from __future__ import annotations

import re

from .opcodes import _OPCODE_NAMES, _PUSH_SIZES


def decode_bytecode(hex_bytes: str) -> list[dict]:
    """Decode hex bytecode into a list of {offset, mnemonic, arguments} dicts."""
    if hex_bytes.startswith("0x"):
        hex_bytes = hex_bytes[2:]
    # Bytecode may contain linker placeholders like __$...$__ (34 hex chars).
    # Replace them with zeros so the decoder can proceed.
    hex_bytes = re.sub(r"__\$[0-9a-fA-F]{34}\$__", "00" * 20, hex_bytes)
    # Strip trailing metadata hash markers, etc. (non-hex chars)
    hex_bytes = re.sub(r"[^0-9a-fA-F]", "0", hex_bytes)
    if len(hex_bytes) % 2:
        hex_bytes = hex_bytes[:-1]  # truncate odd nibble
    if not hex_bytes:
        return []

    data = bytes.fromhex(hex_bytes)
    instructions: list[dict] = []
    i = 0
    while i < len(data):
        opcode = data[i]
        offset = i
        push_size = _PUSH_SIZES.get(opcode)
        if push_size is not None:
            arg_bytes = data[i + 1 : i + push_size]
            arg_hex = "0x" + arg_bytes.hex() if arg_bytes else "0x00"
            instructions.append(
                {
                    "offset": offset,
                    "mnemonic": f"PUSH{push_size - 1}",
                    "arguments": [arg_hex],
                }
            )
            i += push_size
        else:
            instructions.append(
                {
                    "offset": offset,
                    "mnemonic": _OPCODE_NAMES.get(opcode, f"0x{opcode:02x}"),
                    "arguments": [],
                }
            )
            i += 1
    return instructions


def decode_source_map(source_map: str) -> list[dict]:
    """
    Decode a compressed solc source map into one dict per instruction.

    Each entry: {"s": int, "l": int, "f": int, "j": str, "m": int}
    Missing fields inherit from the previous entry.
    """
    entries: list[dict] = []
    prev: dict = {"s": -1, "l": -1, "f": -1, "j": "-", "m": 0}

    for part in source_map.split(";"):
        fields = part.split(":")
        entry = dict(prev)

        def _field(idx: int, cast=int) -> None:
            nonlocal fields, entry
            if idx < len(fields) and fields[idx]:
                key = ("s", "l", "f", "j", "m")[idx]
                try:
                    entry[key] = cast(fields[idx])
                except (ValueError, TypeError):
                    pass

        _field(0)
        _field(1)
        _field(2)
        _field(3, str)
        _field(4)

        entries.append(dict(entry))
        prev = entry

    return entries
