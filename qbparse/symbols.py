from __future__ import annotations

from typing import TYPE_CHECKING, Any

from qbparse.datatypes import Type

if TYPE_CHECKING:
    from qbparse.ast import ProcDefinition


class Procedure:
    def __init__(self, name: str, impls: list[ProcDefinition]):
        self.name = name
        self.impls = impls

    def __repr__(self):
        return f"Procedure(name={self.name}, signatures={self.sigs()})"

    def __eq__(self, other: object):
        if not isinstance(other, Procedure):
            return NotImplemented
        return self.name == other.name and self.sigs() == other.sigs()

    def sigs(self):
        return [i.signature for i in self.impls]


class Variable:
    def __init__(self, name: str, type: Type):
        self.name = name
        self.type = type

    def __repr__(self):
        return f"[Variable name={self.name} type={self.type}]"

    def __eq__(self, other: Any):
        if type(self) is not type(other):
            return NotImplemented
        return self.name == other.name and self.type == other.type
