import struct
from typing import Any


class Type:
    def __init__(self, name: str, min: int | float = 0, max: int | float = 0):
        self.name = name
        self.min = min
        self.max = max

    def __repr__(self):
        return f"[Type {self.name}]"


class FixedWidthType(Type):
    @staticmethod
    def of_string(width: int):
        return FixedWidthType(BUILTIN_TYPES["string"], width)

    @staticmethod
    def of_bit(width: int):
        return FixedWidthType(
            BUILTIN_TYPES["_bit"], width, -(2 ** (width - 1)), 2 ** (width - 1) - 1
        )

    @staticmethod
    def of_unsigned_bit(width: int):
        return FixedWidthType(BUILTIN_TYPES["_unsigned _bit"], width, 0, 2**width - 1)

    def __init__(self, base_type: Type, width: int, min: int = 0, max: int = 0):
        super().__init__(base_type.name + " * " + str(width), min, max)
        self.base_type = base_type
        self.width = width


class TypeSignature:
    def __init__(self, ret: Type, params: list[Type]):
        self.ret = ret
        self.params = params

    def __repr__(self):
        return f"[TypeSignature ret={self.ret} params={self.params}]"

    def __eq__(self, other: Any):
        if type(self) is not type(other):
            return NotImplemented
        return self.ret == other.ret and self.params == other.params


def bits2float(spec1: str, spec2: str, b: int):
    return struct.unpack(">" + spec1, struct.pack(">" + spec2, b))[0]


BUILTIN_TYPES = {
    "_none": Type("_none"),
    "_bit": Type("_bit", -(2**0), 2**0 - 1),
    "_byte": Type("_byte", -(2**7), 2**7 - 1),
    "integer": Type("integer", -(2**15), 2**15 - 1),
    "long": Type("long", -(2**31), 2**31 - 1),
    "_integer64": Type("_integer64", -(2**63), 2**63 - 1),
    # "_offset": Type("_offset"),
    "_unsigned _bit": Type("_unsigned _bit", 0, 2**0),
    "_unsigned _byte": Type("_unsigned _byte", 0, 2**8 - 1),
    "_unsigned integer": Type("_unsigned integer", 0, 2**16 - 1),
    "_unsigned long": Type("_unsigned long", 0, 2**32 - 1),
    "_unsigned _integer64": Type("_unsigned _integer64", 0, 2**64 - 1),
    # "_unsigned _offset": Type("_unsigned _offset"),
    "single": Type(
        "single", bits2float("f", "L", 0xFF7FFFFF), bits2float("f", "L", 0x7F7FFFFF)
    ),
    "double": Type(
        "double",
        bits2float("d", "Q", 0xFFEFFFFFFFFFFFFF),
        bits2float("d", "Q", 0x7FEFFFFFFFFFFFFF),
    ),
    # The "_float" type needs to be an 80 bit extended precision type but Python cannot
    # represent those values, so its bounds are implied.
    "_float": Type("_float"),
    "string": Type("string"),
}

BUILTIN_SIGILS = {
    "`": BUILTIN_TYPES["_bit"],
    "%%": BUILTIN_TYPES["_byte"],
    "%": BUILTIN_TYPES["integer"],
    "&": BUILTIN_TYPES["long"],
    "&&": BUILTIN_TYPES["_integer64"],
    # "%&": BUILTIN_TYPES["_offset"],
    "~`": BUILTIN_TYPES["_unsigned _bit"],
    "~%%": BUILTIN_TYPES["_unsigned _byte"],
    "~%": BUILTIN_TYPES["_unsigned integer"],
    "~&": BUILTIN_TYPES["_unsigned long"],
    "~&&": BUILTIN_TYPES["_unsigned _integer64"],
    # "~%&": BUILTIN_TYPES["_unsigned _offset"],
    "!": BUILTIN_TYPES["single"],
    "#": BUILTIN_TYPES["double"],
    "##": BUILTIN_TYPES["_float"],
    "$": BUILTIN_TYPES["string"],
}
