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


class Variable:
    def __init__(self, name: str, typ: Type):
        self.name = name
        self.typ = typ
