from __future__ import annotations

class Data(bytes):
    @staticmethod
    def zero() -> Data:
        return Data()

    @staticmethod
    def from_int(value: int) -> Data:
        if value == 0:
            return Data.zero()

        byte_count = (value.bit_length() + 7) // 8
        bytes_ = value.to_bytes(byte_count, byteorder="big")
        return Data(bytes_)

    @staticmethod
    def from_hex(hex_str: str) -> Data:
        if not hex_str.startswith("0x"):
            raise ValueError('Invalid hex string format. Expected "0x" prefix.')
        return Data(bytes.fromhex(hex_str[2:]))

    @staticmethod
    def from_bytes(bytes_: bytes) -> Data:
        return Data(bytes_)

    def as_uint(self) -> int:
        return int.from_bytes(self, byteorder="big")

    def to_hex(self) -> str:
        return f"0x{self.hex()}"

    def pad_until_at_least(self, length: int) -> Data:
        if len(self) >= length:
            return self

        padded = bytes(length)
        padded[length - len(self):] = self
        return Data(padded)

    def resize_to(self, length: int) -> Data:
        if len(self) == length:
            return self

        if len(self) < length:
            resized = bytearray(length)
            resized[length - len(self):] = self
            resized = bytes(resized)
        else:
            resized = self[-length:]

        return Data(resized)

    def concat(self, *others: Data) -> Data:
        concatenated = b"".join([self] + list(others))
        return Data(concatenated)

    def __repr__(self) -> str:
        return f"Data[{self.to_hex()}]"
