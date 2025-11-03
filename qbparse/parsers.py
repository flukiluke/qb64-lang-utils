from collections.abc import Callable

from qbparse.ast import Assignment, Expr, If, Print, Statement
from qbparse.context import ParseContext
from qbparse.errors import ParseError
from qbparse.expression import do_expr, do_lvalue


def do_print(ctx: ParseContext):
    """
    Expects: PRINT or ?
    Results: token after last expression, comma or semicolon
    Format: PRINT|? (expr|,|;)*
    """
    next(ctx)
    result = Print()
    final_newline = True
    while not ctx.at_line_terminator():
        match ctx.tok.type, ctx.tok.value:
            case "PUNCTUATION", ",":
                result.params.append(Print.TAB_SEPARATOR)
                final_newline = False
                next(ctx)
            case "PUNCTUATION", ";":
                final_newline = False
                next(ctx)
            case _:
                result.params.append(do_expr(ctx))
                final_newline = True
    if final_newline:
        result.params.append(Print.FINAL_NEWLINE)
    return result


def do_if(ctx: ParseContext):
    """
    Expects: IF
    Results: newline
    """

    def single_line_block(then_section: bool) -> list[Statement]:
        stmts: list[Statement] = []
        ctx.skip("NEWLINE", ":")
        while not (
            ctx.at_a("NEWLINE", "\n")
            or ctx.at_a("EOF")
            or (then_section and ctx.at_a("KEYWORD", "else"))
        ):
            stmt = do_stmt(ctx)
            if stmt:
                stmts.append(stmt)
            ctx.skip("NEWLINE", ":")
        return stmts

    next(ctx)
    guard = do_expr(ctx)
    ctx.consume("KEYWORD", "then")
    # A REM after THEN acts as a command; we remain in single-line if mode
    if ctx.at_a("NEWLINE", "rem"):
        next(ctx)
        return If(guard, [], [], [])

    elses = []
    elseifs: list[tuple[Expr, list[Statement]]] = []
    if not ctx.at_a("NEWLINE", "\n"):
        # Single-line IF
        thens = single_line_block(then_section=True)
        if ctx.at_a("KEYWORD", "else"):
            next(ctx)
            elses = single_line_block(then_section=False)
    else:
        thens = do_block(ctx)
        while ctx.at_a("KEYWORD", "elseif"):
            next(ctx)
            elseif_guard = do_expr(ctx)
            ctx.consume("KEYWORD", "then")
            elseif_thens = do_block(ctx)
            elseifs.append((elseif_guard, elseif_thens))
        if ctx.at_a("KEYWORD", "else"):
            next(ctx)
            elses = do_block(ctx)
        if ctx.at_a("KEYWORD", "endif"):
            next(ctx)
        else:
            ctx.consume("KEYWORD", "if")
    return If(guard, thens, elseifs, elses)


KEYWORD_PARSERS: dict[str, Callable[[ParseContext], Statement]] = {
    "print": do_print,
    "?": do_print,
    "if": do_if,
}


def do_block(ctx: ParseContext) -> list[Statement]:
    """
    Expects: start of statement
    Results: End of block marker
    Note: The end of block marker is:
        - <x> for END <x> keywords (x=IF, SELECT, SUB, FUNCTION),
        - the keyword itself for ELSE, ELSEIF, ENDIF, LOOP, NEXT, WEND, CASE
        - The SUB or FUNCTION keywords (indicating a change of scope)
        - EOF
    """

    def is_eob():
        match ctx.tok.type, ctx.tok.value:
            case "EOF", _:
                return True
            case "KEYWORD", (
                "else"
                | "elseif"
                | "endif"
                | "loop"
                | "next"
                | "wend"
                | "case"
                | "sub"
                | "function"
            ):
                return True
            case "KEYWORD", "end":
                end = ctx.tok
                next(ctx)
                if not ctx.at_line_terminator():
                    return True
                else:
                    ctx.reverse(end)
                    return False
            case _:
                return False

    block: list[Statement] = []
    ctx.skip("NEWLINE")
    while not is_eob():
        stmt = do_stmt(ctx)
        if stmt:
            block.append(stmt)
        ctx.skip("NEWLINE")
    return block


def do_stmt(ctx: ParseContext) -> Statement | None:
    result = None
    ctx.skip("NEWLINE")
    match ctx.tok.type:
        case "KEYWORD":
            handler = KEYWORD_PARSERS.get(ctx.tok.value)
            if handler is None:
                raise ParseError("Unexpected keyword " + ctx.tok.value)
            result = handler(ctx)
        case "VARIABLE":
            # Asignment to existing variable
            result = do_assignment(ctx)
        case "PROCEDURE":
            # Call to existing procedure
            result = do_procedure_call(ctx)
        case "ID":
            # May be assignment to new variable, or call
            # to not-yet-defined procedure
            result = do_unknown_var_or_procedure(ctx)
        case _:
            raise ParseError(f"Unexpected {ctx.tok.type} {ctx.tok.value}")
    return result


def do_unknown_var_or_procedure(ctx: ParseContext) -> Statement:
    tok = ctx.tok
    next(ctx)
    if ctx.at_a("PUNCTUATION", "="):
        # Assignment to an implicitly declared scalar variable
        ctx.reverse(tok)
        return do_assignment(ctx)
    elif ctx.at_a("PUNCTUATION", "("):
        # This could be either an implicit array declaration or a
        # call to an unknown subprocedure.
        raise ParseError("Unimplemented implicit array")
    else:
        raise ParseError("Unimplemented procedure call")


def do_assignment(ctx: ParseContext):
    """
    Expects: first token of lvalue
    Results: token after rvalue
    """
    lval = do_lvalue(ctx)
    ctx.consume("PUNCTUATION", "=")
    rval = do_expr(ctx)
    return Assignment(lval, rval)


def do_procedure_call(ctx: ParseContext):
    pass
