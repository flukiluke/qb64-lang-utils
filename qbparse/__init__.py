from qbparse.ast import ProcDefinition
from qbparse.context import ParseContext
from qbparse.datatypes import TYPE__NONE, TypeSignature
from qbparse.parsers import do_block
from qbparse.symbols import Procedure, SymbolStore


class Program:
    def __init__(self):
        self.globals = SymbolStore()


def parse(input: str):
    program = Program()
    ctx = ParseContext(input, program.globals)
    main = Procedure("_main", TypeSignature(TYPE__NONE, []))
    main.impl = ProcDefinition()
    program.globals.procedures["_main"] = main
    main.impl.statements = do_block(ctx)
    return program
