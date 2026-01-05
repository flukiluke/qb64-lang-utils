from collections.abc import Callable

import qbparse.diagnostics as diag
from qbparse.ast import (
    Assignment,
    Call,
    Constant,
    Expr,
    For,
    If,
    Loop,
    Print,
    Statement,
)
from qbparse.context import ParseContext
from qbparse.datatypes import TYPE__BYTE
from qbparse.diagnostics import ParseError
from qbparse.expression import do_bare_var, do_expr, do_lvalue


def do_print(ctx: ParseContext):
    """
    Expects: PRINT or ?
    Format: PRINT|? (expr|,|;)*
    """
    result = Print(lex_start=ctx.tok.lexpos, lex_len=ctx.tok.length)
    next(ctx)
    final_newline = True
    while not ctx.at_line_terminator():
        match ctx.tok.type, ctx.tok.value:
            case "PUNCTUATION", ",":
                result.args.append(Print.TAB_SEPARATOR)
                final_newline = False
                next(ctx)
            case "PUNCTUATION", ";":
                final_newline = False
                next(ctx)
            case _:
                result.args.append(do_expr(ctx))
                final_newline = True
    if final_newline:
        result.args.append(Print.FINAL_NEWLINE)
    return result


def do_if(ctx: ParseContext):
    """
    Expects: IF
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

    lex_start = ctx.tok.lexpos
    next(ctx)
    guard = do_expr(ctx)
    ctx.consume("KEYWORD", "then")
    # A REM after THEN acts as a command; we remain in single-line if mode
    if ctx.at_a("NEWLINE", "rem"):
        # Do not advance token so we leave it at a NEWLINE
        return If(
            guard,
            [],
            [],
            [],
            lex_start=lex_start,
            lex_len=(ctx.prev.lexpos + ctx.prev.length - lex_start),
        )

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
        elif ctx.prev.type == "KEYWORD" and ctx.prev.value == "end":
            ctx.consume("KEYWORD", "if")
        else:
            ctx.diags.raise_error(
                diag.E_UNEXPECTED_ITEM, ctx.tok, ctx.tok.value, "end if"
            )
    return If(guard, thens, elseifs, elses, lex_start=lex_start)


def do_do(ctx: ParseContext):
    """
    Expects: DO
    """

    def loop_guard() -> Expr | None:
        if ctx.at_a("KEYWORD", "while"):
            next(ctx)
            return do_expr(ctx)
        elif ctx.at_a("KEYWORD", "until"):
            next(ctx)
            return Call(
                ctx.symbols.procedures["<>"],
                [do_expr(ctx), Constant(0, TYPE__BYTE)],
                lex_start=ctx.prev.lexpos,
            )
        elif ctx.at_line_terminator():
            return None
        else:
            ctx.diags.raise_error(
                diag.E_UNEXPECTED_ITEM,
                ctx.tok,
                ctx.tok.value,
                "while or until or <newline>",
            )

    lex_start = ctx.tok.lexpos
    next(ctx)
    top = loop_guard()
    ctx.consume("NEWLINE")
    block = do_block(ctx)
    loop_tok = ctx.tok
    ctx.consume("KEYWORD", "loop")
    lex_end = ctx.prev.lexpos + ctx.prev.length
    bottom = loop_guard()
    if top and bottom:
        ctx.diags.create(diag.E_TOO_MANY_LOOP_GUARDS, loop_tok)
        guard = top
    elif top:
        guard = top
    elif bottom:
        guard = bottom
    else:
        guard = Constant(1, TYPE__BYTE)
    return Loop(
        guard,
        block,
        top_check=(top is not None),
        lex_start=lex_start,
        lex_len=(lex_end - lex_start),
    )


def do_while(ctx: ParseContext):
    """
    Expects: WHILE
    """
    lex_start = ctx.tok.lexpos
    next(ctx)
    guard = do_expr(ctx)
    ctx.consume("NEWLINE")
    block = do_block(ctx)
    ctx.consume("KEYWORD", "wend")
    return Loop(
        guard,
        block,
        top_check=True,
        lex_start=lex_start,
        lex_len=(ctx.prev.lexpos + ctx.prev.length - lex_start),
    )


def do_for(ctx: ParseContext):
    """
    Expects: FOR
    """
    lex_start = ctx.tok.lexpos
    next(ctx)
    var = do_bare_var(ctx)
    ctx.consume("PUNCTUATION", "=")
    start_value = do_expr(ctx)
    ctx.consume("KEYWORD", "to")
    end_value = do_expr(ctx)
    if ctx.at_a("KEYWORD", "step"):
        next(ctx)
        step_value = do_expr(ctx)
    elif ctx.at_a("NEWLINE"):
        step_value = Constant(1, var.target.type)
    else:
        ctx.diags.raise_error(
            diag.E_UNEXPECTED_ITEM, ctx.tok, ctx.tok.value, "step or <newline>"
        )
    ctx.consume("NEWLINE")
    block = do_block(ctx)
    ctx.consume("KEYWORD", "next")
    if not ctx.at_line_terminator():
        next_var_tok = ctx.tok
        next_var = do_bare_var(ctx)
        if var.target != next_var.target:
            ctx.diags.raise_error(
                diag.E_FOR_NEXT_VAR_MISMATCH,
                next_var_tok,
                next_var.target.name,
                var.target.name,
            )
    return For(
        var,
        start_value,
        end_value,
        step_value,
        block,
        lex_start=lex_start,
        lex_len=(ctx.prev.lexpos + ctx.prev.length - lex_start),
    )


KEYWORD_PARSERS: dict[str, Callable[[ParseContext], Statement]] = {
    "print": do_print,
    "?": do_print,
    "if": do_if,
    "do": do_do,
    "while": do_while,
    "for": do_for,
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
                next(ctx)
                if not ctx.at_line_terminator():
                    return True
                else:
                    ctx.reverse()
                    return False
            case _:
                return False

    block: list[Statement] = []
    ctx.skip("NEWLINE")
    while not is_eob():
        try:
            stmt = do_stmt(ctx)
        except diag.DiagnosticError:
            stmt = None
            while not ctx.at_line_terminator():
                next(ctx)
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
                ctx.diags.raise_error(diag.E_UNEXPECTED_KEYWORD, ctx.tok, ctx.tok.value)
            result = handler(ctx)
            if not ctx.at_line_terminator():
                ctx.diags.raise_error(
                    diag.E_UNEXPECTED_ITEM, ctx.tok, ctx.tok.value, "end of statement"
                )
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
            ctx.diags.raise_error(
                diag.E_UNEXPECTED_ITEM, ctx.tok, ctx.tok.value, "a statement"
            )
    return result


def do_unknown_var_or_procedure(ctx: ParseContext) -> Statement:
    next(ctx)
    if ctx.at_a("PUNCTUATION", "="):
        # Assignment to an implicitly declared scalar variable
        ctx.reverse()
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
    """
    lval = do_lvalue(ctx)
    ctx.consume("PUNCTUATION", "=")
    rval = do_expr(ctx)
    return Assignment(lval, rval)


def do_procedure_call(ctx: ParseContext):
    pass
