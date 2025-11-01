from typing import Any


class Type:
    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return f"[Type {self.name}]"


class FixedWidthType(Type):
    def __init__(self, base_type: Type, width: int):
        self.base_type = base_type
        self.width = width
        self.name = self.base_type.name + " * " + str(width)


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


BUILTIN_TYPES = {
    "_none": Type("_none"),
    "_bit": Type("_bit"),
    "_byte": Type("_byte"),
    "integer": Type("integer"),
    "long": Type("long"),
    "_integer64": Type("_integer64"),
    "_offset": Type("_offset"),
    "_unsigned _bit": Type("_unsigned _bit"),
    "_unsigned _byte": Type("_unsigned _byte"),
    "_unsigned integer": Type("_unsigned integer"),
    "_unsigned long": Type("_unsigned long"),
    "_unsigned _integer64": Type("_unsigned _integer64"),
    "_unsigned _offset": Type("_unsigned _offset"),
    "single": Type("single"),
    "double": Type("double"),
    "_float": Type("_float"),
    "string": Type("string"),
}

BUILTIN_SIGILS = {
    "`": BUILTIN_TYPES["_bit"],
    "%%": BUILTIN_TYPES["_byte"],
    "%": BUILTIN_TYPES["integer"],
    "&": BUILTIN_TYPES["long"],
    "&&": BUILTIN_TYPES["_integer64"],
    "%&": BUILTIN_TYPES["_offset"],
    "~`": BUILTIN_TYPES["_unsigned _bit"],
    "~%%": BUILTIN_TYPES["_unsigned _byte"],
    "~%": BUILTIN_TYPES["_unsigned integer"],
    "~&": BUILTIN_TYPES["_unsigned long"],
    "~&&": BUILTIN_TYPES["_unsigned _integer64"],
    "~%&": BUILTIN_TYPES["_unsigned _offset"],
    "!": BUILTIN_TYPES["single"],
    "#": BUILTIN_TYPES["double"],
    "##": BUILTIN_TYPES["_float"],
    "$": BUILTIN_TYPES["string"],
}
