import pytest
from ethdebug.data import Data

def test_correctly_converts_to_integers_big_endian():
    data = Data([0x01, 0x00])
    assert str(data.as_uint()) == "256"

def test_correctly_creates_data_instances_from_ints():
    data1 = Data.from_int(0)
    assert data1 == Data([])

    data2 = Data.from_int(255)
    assert data2 == Data([0xFF])

    data3 = Data.from_int(256)
    assert data3 == Data([0x01, 0x00])

    data4 = Data.from_int(1234567890)
    assert data4 == Data([0x49, 0x96, 0x02, 0xD2])

def test_correctly_creates_data_instances_from_hex_strings():
    data1 = Data.from_hex("0x00")
    assert data1 == Data([0x00])

    data2 = Data.from_hex("0xFF")
    assert data2 == Data([0xFF])

    data3 = Data.from_hex("0x0100")
    assert data3 == Data([0x01, 0x00])

    data4 = Data.from_hex("0x499602D2")
    assert data4 == Data([0x49, 0x96, 0x02, 0xD2])

def test_throws_error_for_invalid_hex_string_format():
    with pytest.raises(ValueError, match="Invalid hex string format. Expected \"0x\" prefix."):
        Data.from_hex("ff")