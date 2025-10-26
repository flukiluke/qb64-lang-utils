from datatypes import TypeSignature


class Statement:
    pass


class Procedure:
    def __init__(self, name: str, signature: TypeSignature | None):
        self.name = name
        # signature may be None for special cased procedures
        self.signature = signature
        self.children: list[Statement] = []
