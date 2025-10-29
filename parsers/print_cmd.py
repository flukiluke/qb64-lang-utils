from ast_nodes import Print
from parsers.context import ParseContext

from . import expression


def parse(ctx: ParseContext):
    """
    Expects: PRINT or ?
    Results: token after last expression, comma or semicolon
    Format: PRINT|? (expr|,|;)*
    """
    next(ctx)
    result = Print()
    final_newline = True
    while not ctx.at_line_terminator():
        match ctx.tok.type:
            case "COMMA":
                result.params.append(Print.TAB_SEPARATOR)
                final_newline = False
            case "SEMICOLON":
                final_newline = False
            case _:
                result.params.append(expression.parse(ctx))
                final_newline = True
    if final_newline:
        result.params.append(Print.FINAL_NEWLINE)
    return result
