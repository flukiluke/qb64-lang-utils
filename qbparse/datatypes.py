import struct
from dataclasses import dataclass
from functools import total_ordering
from typing import Any


@total_ordering
class ExtendedFloat:
    """
    A Python float can't store the 80 bit extended precision type needed to support
    _FLOAT, so they are represented as a (sign, mantissa, exponent) tuple where the
    exponent is base 10 and the mantissa has an implicit leading 0., hence
    -1.2 = -0.12 * 10^1 = (-1, "12", 1).
    """

    def __init__(self, mantissa: str, exp: str = "0"):
        int_exp = int(exp)
        self.sign = 1
        if mantissa.startswith("-"):
            mantissa = mantissa[1:]
            self.sign = -1
        mantissa = mantissa.lstrip("0")
        index = mantissa.find(".")
        if index >= 0:
            self.mantissa = mantissa.replace(".", "", count=1).rstrip("0")
            int_exp += index
        else:
            self.mantissa = mantissa.rstrip("0")
            int_exp += len(mantissa)
        self.exponent = int_exp

    def __repr__(self):
        return (
            ("-" if self.sign == -1 else "+")
            + self.mantissa[0]
            + "."
            + self.mantissa[1:]
            + "E"
            + str(self.exponent - 1)
        )

    def __int__(self):
        if self.exponent == 0:
            return 0
        return int(self.mantissa[: self.exponent].ljust(self.exponent, "0"))

    def to_float(self):
        return float(repr(self))

    def __eq__(self, other: object):
        if not isinstance(other, ExtendedFloat):
            return NotImplemented
        return (
            self.sign == other.sign
            and self.mantissa == other.mantissa
            and self.exponent == other.exponent
        )

    def __lt__(self, other: object):
        if not isinstance(other, ExtendedFloat):
            return NotImplemented
        if self.sign != other.sign:
            return self.sign < other.sign
        if self.exponent != other.exponent:
            return self.sign * self.exponent < self.sign * other.exponent
        for a, b in zip(self.mantissa, other.mantissa):
            if a < b:
                return self.sign == 1
            if a > b:
                return self.sign == -1
        return self.sign * len(self.mantissa) < self.sign * len(other.mantissa)


@dataclass
class Type:
    name: str

    def __repr__(self):
        return f"[Type {self.name}]"


@dataclass
class FloatType(Type):
    min: float | ExtendedFloat
    max: float | ExtendedFloat

    def __repr__(self):
        return f"[Type {self.name}]"


@dataclass
class IntegralType(Type):
    min: int
    max: int

    def __repr__(self):
        return f"[Type {self.name}]"


@dataclass
class StringType(Type):
    max_len: int | None = None

    @staticmethod
    def of_max_len(max_len: int):
        return StringType("string * " + str(max_len), max_len)

    def __repr__(self):
        return f"[Type {self.name}]"


@dataclass
class BitnType(IntegralType):
    width: int

    @staticmethod
    def of_signed(width: int):
        return BitnType(
            "_bit * " + str(width), -(2 ** (width - 1)), 2 ** (width - 1) - 1, width
        )

    @staticmethod
    def of_unsigned(width: int):
        return BitnType("_unsigned _bit * " + str(width), 0, 2**width - 1, width)

    def __repr__(self):
        return f"[Type {self.name}]"


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


TYPE__NONE = Type("_none")
TYPE__BIT = IntegralType("_bit", -(2**0), 2**0 - 1)
TYPE__BYTE = IntegralType("_byte", -(2**7), 2**7 - 1)
TYPE_INTEGER = IntegralType("integer", -(2**15), 2**15 - 1)
TYPE_LONG = IntegralType("long", -(2**31), 2**31 - 1)
TYPE__INTEGER64 = IntegralType("_integer64", -(2**63), 2**63 - 1)
TYPE__UNSIGNED__BIT = IntegralType("_unsigned _bit", 0, 2**0)
TYPE__UNSIGNED__BYTE = IntegralType("_unsigned _byte", 0, 2**8 - 1)
TYPE__UNSIGNED_INTEGER = IntegralType("_unsigned integer", 0, 2**16 - 1)
TYPE__UNSIGNED_LONG = IntegralType("_unsigned long", 0, 2**32 - 1)
TYPE__UNSIGNED__INTEGER64 = IntegralType("_unsigned _integer64", 0, 2**64 - 1)
TYPE_SINGLE = FloatType(
    "single", bits2float("f", "L", 0xFF7FFFFF), bits2float("f", "L", 0x7F7FFFFF)
)
# A number outside the double range will be converted to inf by Python so the range
# checking doesn't actually need these values.
TYPE_DOUBLE = FloatType(
    "double",
    bits2float("d", "Q", 0xFFEFFFFFFFFFFFFF),
    bits2float("d", "Q", 0x7FEFFFFFFFFFFFFF),
)
# Originally intended to be a x87 80 bit float, but allowed to be a 128 bit float.
# Limits assume the former (approximate values).
TYPE__FLOAT = FloatType(
    "_float",
    ExtendedFloat("-1.18973149535723176502126", "4932"),
    ExtendedFloat("1.18973149535723176502126", "4932"),
)
TYPE_STRING = StringType("string")

BUILTIN_TYPES: dict[str, Type] = {
    "_none": TYPE__NONE,
    "_bit": TYPE__BIT,
    "_byte": TYPE__BYTE,
    "integer": TYPE_INTEGER,
    "long": TYPE_LONG,
    "_integer64": TYPE__INTEGER64,
    "_unsigned _bit": TYPE__UNSIGNED__BIT,
    "_unsigned _byte": TYPE__UNSIGNED__BYTE,
    "_unsigned integer": TYPE__UNSIGNED_INTEGER,
    "_unsigned long": TYPE__UNSIGNED_LONG,
    "_unsigned _integer64": TYPE__UNSIGNED__INTEGER64,
    "single": TYPE_SINGLE,
    "double": TYPE_DOUBLE,
    "_float": TYPE__FLOAT,
    "string": TYPE_STRING,
}

BUILTIN_SIGILS: dict[str, Type] = {
    "`": TYPE__BIT,
    "%%": TYPE__BYTE,
    "%": TYPE_INTEGER,
    "&": TYPE_LONG,
    "&&": TYPE__INTEGER64,
    "~`": TYPE__UNSIGNED__BIT,
    "~%%": TYPE__UNSIGNED__BYTE,
    "~%": TYPE__UNSIGNED_INTEGER,
    "~&": TYPE__UNSIGNED_LONG,
    "~&&": TYPE__UNSIGNED__INTEGER64,
    "!": TYPE_SINGLE,
    "#": TYPE_DOUBLE,
    "##": TYPE__FLOAT,
    "$": TYPE_STRING,
}
