from ast_nodes import Procedure, Statement
from datatypes import BUILTIN_TYPES, TypeSignature
from errors import ParseError
from parsers.context import ParseContext

from . import print_cmd

KEYWORD_PARSERS = {
    "print": print_cmd.parse,
    "?": print_cmd.parse,
}


def parse(input: str):
    ctx = ParseContext(input)
    main = Procedure("_main", TypeSignature(BUILTIN_TYPES["_none"], []))
    ctx.symbols.procedures["_main"] = main
    while (
        not ctx.at_a("EOF")
        and not ctx.at_a("KEYWORD", "sub")
        and not ctx.at_a("KEYWORD", "function")
    ):
        stmt = do_stmt(ctx)
        if stmt:
            main.statements.append(stmt)
    return ctx.symbols


def do_stmt(ctx: ParseContext) -> Statement | None:
    result = None
    if ctx.tok.type == "KEYWORD":
        handler = KEYWORD_PARSERS.get(ctx.tok.value)
        if handler is None:
            raise ParseError("Unexpected keyword " + ctx.tok.value)
        result = handler(ctx)
    ctx.skip("NEWLINE", "LINE_SPLIT")
    return result
