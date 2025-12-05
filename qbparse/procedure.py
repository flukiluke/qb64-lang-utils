from __future__ import annotations

from typing import TYPE_CHECKING

from qbparse.datatypes import TypeSignature

if TYPE_CHECKING:
    from qbparse.ast import ProcDefinition


class Procedure:

    def __init__(self, name: str, impls: list[ProcDefinition]):
        self.name = name
        self._impls = impls
        self._signatures = [i.signature for i in impls]

    def __repr__(self):
        return f"Procedure(name={self.name}, signatures={self._signatures})"

    def __eq__(self, other: object):
        if not isinstance(other, Procedure):
            return NotImplemented
        return self.name == other.name and self._signatures == other._signatures

    def impls(self):
        return self._impls
    
    def sigs(self):
        return self._signatures

class BuiltinProcedure(Procedure):

    def __init__(self, name: str, signatures: list[TypeSignature]):
        self.name = name
        self._signatures = signatures
        self._impls = []

    def __repr__(self):
        return f"BuiltinProcedure(name={self.name}, signatures={self._signatures})"
