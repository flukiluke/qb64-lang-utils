from qbparse.ast import ProcDefinition
from qbparse.context import ParseContext
from qbparse.datatypes import BUILTIN_TYPES, TypeSignature
from qbparse.parsers import do_stmt
from qbparse.symbols import Procedure, SymbolStore


class Program:
    def __init__(self):
        self.globals = SymbolStore()


def parse(input: str):
    program = Program()
    ctx = ParseContext(input, program.globals)
    main = Procedure("_main", TypeSignature(BUILTIN_TYPES["_none"], []))
    main.impl = ProcDefinition()
    program.globals.procedures["_main"] = main
    while (
        not ctx.at_a("EOF")
        and not ctx.at_a("KEYWORD", "sub")
        and not ctx.at_a("KEYWORD", "function")
    ):
        stmt = do_stmt(ctx)
        if stmt:
            main.impl.statements.append(stmt)
    return program
