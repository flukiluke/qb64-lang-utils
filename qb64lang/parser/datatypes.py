import struct
from dataclasses import dataclass
from functools import total_ordering

from . import diagnostics as diag
from .ply import LexToken


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
            self.mantissa = mantissa.replace(".", "", 1).rstrip("0")
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
    source_name: str
    sigil: str

    def __repr__(self):
        return self.name

    def is_number(self) -> bool:
        return False

    def is_builtin(self) -> bool:
        return True


@dataclass
class ArrayType(Type):
    element_type: Type
    dimensions: int

    def is_builtin(self):
        return False

    def undim_name(self):
        return self.element_type.name + "[0]"


@dataclass
class CompoundField:
    type: Type
    name: str
    source_name: str


@dataclass
class CompoundType(Type):
    fields: list[CompoundField]

    def is_builtin(self):
        return False

    def get_field(self, name: str):
        for field in self.fields:
            if field.name == name:
                return field
        return None


@dataclass
class FloatType(Type):
    min: float | ExtendedFloat
    max: float | ExtendedFloat
    # Range of integers that can be exactly represented by this type
    min_int: int
    max_int: int

    def __repr__(self):
        return super().__repr__()

    def is_number(self):
        return True


@dataclass
class IntegralType(Type):
    min: int
    max: int

    def __repr__(self):
        return super().__repr__()

    def is_number(self):
        return True


@dataclass
class StringType(Type):
    max_len: int | None = None

    def __repr__(self):
        return super().__repr__()

    @staticmethod
    def of_max_len(max_len: int):
        suffix = str(max_len)
        return StringType(
            "string * " + suffix, "String * " + suffix, "$" + suffix, max_len
        )


@dataclass
class BitnType(IntegralType):
    width: int

    def __repr__(self):
        return super().__repr__()

    @staticmethod
    def of_signed(width: int):
        suffix = str(width)
        return BitnType(
            "_bit * " + suffix,
            "_Bit * " + suffix,
            "`" + suffix,
            -(2 ** (width - 1)),
            2 ** (width - 1) - 1,
            width,
        )

    @staticmethod
    def of_unsigned(width: int):
        suffix = str(width)
        return BitnType(
            "_unsigned _bit * " + suffix,
            "_Unsigned _Bit * " + suffix,
            "~`" + suffix,
            0,
            2**width - 1,
            width,
        )

    def is_number(self):
        return True


@dataclass
class Parameter:
    type: Type
    # names may be omitted for builtins
    name: str | None = None
    source_name: str | None = None
    has_sigil: bool = False


@dataclass
class TypeSignature:
    ret: Type
    params: list[Parameter]

    def equivalent_to(self, other: "TypeSignature"):
        return self.ret == other.ret and [p.type for p in self.params] == [
            p.type for p in other.params
        ]


def bits2float(spec1: str, spec2: str, b: int):
    return struct.unpack(">" + spec1, struct.pack(">" + spec2, b))[0]


TYPE__NONE = Type("_none", "_None", "")
TYPE_ANY = Type("any", "Any", "")
TYPE__BIT = IntegralType("_bit", "_Bit", "`", -(2**0), 2**0 - 1)
TYPE__BYTE = IntegralType("_byte", "_Byte", "%%", -(2**7), 2**7 - 1)
TYPE_INTEGER = IntegralType("integer", "Integer", "%", -(2**15), 2**15 - 1)
TYPE_LONG = IntegralType("long", "Long", "&", -(2**31), 2**31 - 1)
TYPE__INTEGER64 = IntegralType("_integer64", "_Integer64", "&&", -(2**63), 2**63 - 1)
TYPE__UNSIGNED__BIT = IntegralType("_unsigned _bit", "_Unsigned _Bit", "~`", 0, 2**0)
TYPE__UNSIGNED__BYTE = IntegralType(
    "_unsigned _byte", "_Unsigned _Byte", "~%%", 0, 2**8 - 1
)
TYPE__UNSIGNED_INTEGER = IntegralType(
    "_unsigned integer", "_Unsigned Integer", "~%", 0, 2**16 - 1
)
TYPE__UNSIGNED_LONG = IntegralType(
    "_unsigned long", "_Unsigned Long", "~&", 0, 2**32 - 1
)
TYPE__UNSIGNED__INTEGER64 = IntegralType(
    "_unsigned _integer64", "_Unsigned _Integer64", "~&&", 0, 2**64 - 1
)
# These must be in increasing size order for function overloads to work
INTEGRAL_TYPES = [
    TYPE__BIT,
    TYPE__UNSIGNED__BIT,
    TYPE__BYTE,
    TYPE__UNSIGNED__BYTE,
    TYPE_INTEGER,
    TYPE__UNSIGNED_INTEGER,
    TYPE_LONG,
    TYPE__UNSIGNED_LONG,
    TYPE__INTEGER64,
    TYPE__UNSIGNED__INTEGER64,
]
TYPE_SINGLE = FloatType(
    "single",
    "Single",
    "!",
    bits2float("f", "L", 0xFF7FFFFF),
    bits2float("f", "L", 0x7F7FFFFF),
    -(2**24),
    2**24,
)
# A number outside the double range will be converted to inf by Python so the range
# checking doesn't actually need these values.
TYPE_DOUBLE = FloatType(
    "double",
    "Double",
    "#",
    bits2float("d", "Q", 0xFFEFFFFFFFFFFFFF),
    bits2float("d", "Q", 0x7FEFFFFFFFFFFFFF),
    -(2**53),
    2**53,
)
# Originally intended to be a x87 80 bit float, but allowed to be a 128 bit float.
# Limits assume the former (approximate values).
TYPE__FLOAT = FloatType(
    "_float",
    "_Float",
    "##",
    ExtendedFloat("-1.18973149535723176502126", "4932"),
    ExtendedFloat("1.18973149535723176502126", "4932"),
    -(2**64),
    2**64,
)
FLOAT_TYPES = [TYPE_SINGLE, TYPE_DOUBLE, TYPE__FLOAT]
TYPE_STRING = StringType("string", "String", "$")

BUILTIN_TYPES: dict[str, Type] = {
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


def can_cast(src: Type, dest: Type):
    """
    Can src be cast to dest, even with loss?
    """
    return can_safely_cast(src, dest) or (src.is_number() and dest.is_number())


def can_safely_cast(src: Type, dest: Type):
    """
    Can src be cast to dest without loss of data?
    """
    if src == dest:
        return True
    if dest == TYPE_ANY:
        return True
    if not src.is_number() or not dest.is_number():
        return False
    if src == TYPE__FLOAT:
        return False
    if dest == TYPE__FLOAT:
        return True
    if isinstance(src, FloatType) and isinstance(dest, IntegralType):
        return False
    if isinstance(src, IntegralType) and isinstance(dest, FloatType):
        return src.min >= dest.min_int and src.max <= dest.max_int
    assert isinstance(src, (IntegralType, FloatType))
    assert isinstance(dest, (IntegralType, FloatType))
    return src.min >= dest.min and src.max <= dest.max


def validate_fixed_width(
    base_type: Type, width: int, t: LexToken, diags: diag.DiagnosticStore
):
    if base_type is TYPE__BIT or base_type is TYPE__UNSIGNED__BIT:
        if width > 64 or width < 1:
            diags.raise_error(diag.E_BAD_TYPE_WIDTH, t, base_type.name, 1, 64)
    elif base_type is TYPE_STRING:
        if width > 2**64 - 1 or width < 1:
            diags.raise_error(diag.E_BAD_TYPE_WIDTH, t, base_type.name, 1, 2**64 - 1)
    else:
        diags.raise_error(diag.E_UNFIXABLE_TYPE, t, base_type.name)
