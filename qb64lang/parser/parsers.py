from collections.abc import Callable

from . import diagnostics as diag
from .ast import (
    Assignment,
    Call,
    Constant,
    Expr,
    For,
    If,
    LocalScope,
    Loop,
    Print,
    ProcDefinitionLocation,
    Procedure,
    SetReturn,
    Statement,
    UserProcDefinition,
)
from .context import ParseContext
from .datatypes import TYPE__BYTE, TYPE__NONE, Parameter, Type, TypeSignature
from .diagnostics import ParseError
from .expression import do_bare_var, do_expr, do_func_args, do_lvalue


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
        elif ctx.at_a("KEYWORD", "end"):
            next(ctx)
            ctx.consume("KEYWORD", "if")
        else:
            ctx.diags.raise_error(
                diag.E_UNEXPECTED_ITEM, ctx.tok, ctx.tok.value, "end if"
            )
    return If(
        guard,
        thens,
        elseifs,
        elses,
        lex_start=lex_start,
        lex_len=(ctx.prev.lexpos + ctx.prev.length - lex_start),
    )


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
        if ctx.at_a("PUNCTUATION", ","):
            # Annoying NEXT k, j, i style. Insert newline + another NEXT token,
            # effectively expanding it to NEXT k : NEXT j, i
            ctx.prev.type = "NEWLINE"
            ctx.prev.value = ":"
            ctx.prev.length = 0
            ctx.tok.type = "KEYWORD"
            ctx.tok.value = "next"
            ctx.tok.length = 0
            ctx.reverse()

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


def is_eob(ctx: ParseContext):
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
            result = not ctx.at_line_terminator()
            ctx.reverse()
            return result
        case _:
            return False


def name_close_match(ctx: ParseContext):
    """
    Assuming ctx is at a closing KEYWORD, give the name of the opening
    KEYWORD it is paired with.
    """
    match ctx.tok.value:
        case "else" | "elseif" | "endif":
            return "if"
        case "loop":
            return "do"
        case "next":
            return "for"
        case "wend":
            return "while"
        case "case":
            return "select"
        case "end":
            next(ctx)
            name = ctx.tok.value
            ctx.reverse()
            return name
        case _:
            return "opening keyword"


def do_main(ctx: ParseContext):
    main = UserProcDefinition("_main", TypeSignature(TYPE__NONE, []), ctx.symbols.scope)
    ctx.symbols.add_procedure(Procedure("_main", [main]))
    while not ctx.at_a("EOF"):
        ctx.symbols.set_scope(main.symbols)
        main.statements.extend(do_block(ctx))
        if ctx.at_a("KEYWORD", "sub") or ctx.at_a("KEYWORD", "function"):
            try:
                main.statements.append(do_sub_function(ctx))
            except diag.DiagnosticError:
                ctx.drop_line()
        elif ctx.at_a("EOF"):
            break
        elif is_eob(ctx):
            ctx.diags.create(
                diag.E_CLOSE_KEYWORD_NO_OPEN,
                ctx.tok,
                ctx.tok.value,
                name_close_match(ctx),
            )
            ctx.drop_line()
    ctx.symbols.set_scope(main.symbols)
    return main


def do_sub_function(ctx: ParseContext) -> ProcDefinitionLocation:
    lex_start = ctx.tok.lexpos
    is_sub = ctx.at_a("KEYWORD", "sub")
    default_type = ctx.symbols.default_type
    try:
        if is_sub:
            ctx.symbols.default_type = TYPE__NONE
        next(ctx)
        if not ctx.at_a("ID"):
            ctx.diags.raise_error(diag.E_NAME_IN_USE, ctx.tok, ctx.tok.value)
        elif not ctx.symbols.is_proc_name_free(ctx.tok.value[0]):
            ctx.diags.raise_error(diag.E_NAME_IN_USE, ctx.tok, ctx.tok.value[0])
    finally:
        ctx.symbols.default_type = default_type
    name: str = ctx.tok.value[0]
    ret: Type = ctx.tok.value[1]
    if is_sub and ret != TYPE__NONE:
        ctx.diags.create(diag.E_SUB_WITH_TYPE, ctx.tok)
    next(ctx)

    # The order of these steps is important to make sure the lexer
    # can resolve things properly
    proc = Procedure(name, [])
    ctx.symbols.add_procedure(proc)
    scope = LocalScope()
    ctx.symbols.set_scope(scope)
    params = do_param_list(ctx)
    impl = UserProcDefinition(name, TypeSignature(ret, params), scope)
    proc.impls.append(impl)
    ctx.current_subproc = impl
    try:
        ctx.consume("NEWLINE")
        impl.statements = do_block(ctx)

        ctx.consume("KEYWORD", "end")
        if ctx.at_a("KEYWORD", "sub"):
            ctx.consume("KEYWORD", "sub")
        else:
            ctx.consume("KEYWORD", "function")
        return ProcDefinitionLocation(
            impl,
            lex_start=lex_start,
            lex_len=(ctx.prev.lexpos + ctx.prev.length - lex_start),
        )
    finally:
        ctx.current_subproc = None


def do_param_list(ctx: ParseContext):
    result = list[Parameter]()
    if not ctx.at_a("PUNCTUATION", "("):
        return result
    ctx.consume("PUNCTUATION", "(")
    while True:
        if not ctx.at_a("ID"):
            ctx.diags.raise_error(diag.E_NAME_IN_USE, ctx.tok, ctx.tok.value)
        name, type = ctx.tok.value
        result.append(Parameter(type, name))
        ctx.symbols.create_local(name, type)
        next(ctx)
        if ctx.at_a("PUNCTUATION", ")"):
            break
        ctx.consume("PUNCTUATION", ",")
    ctx.consume("PUNCTUATION", ")")
    return result


def do_block(ctx: ParseContext) -> list[Statement]:
    """
    Expects: start of statement
    Results: End of block marker
    Note: The end of block marker is:
        - END for END <x> keywords (x=IF, SELECT, SUB, FUNCTION),
        - the keyword itself for ELSE, ELSEIF, ENDIF, LOOP, NEXT, WEND, CASE
        - The SUB or FUNCTION keywords (indicating a change of scope)
        - EOF
    """

    block: list[Statement] = []
    ctx.skip("NEWLINE")
    if ctx.current_subproc is not None and (
        ctx.at_a("KEYWORD", "sub") or ctx.at_a("KEYWORD", "function")
    ):
        ctx.diags.raise_error(diag.E_NESTED_PROC, ctx.tok)
    while not is_eob(ctx):
        try:
            stmt = do_stmt(ctx)
        except diag.DiagnosticError:
            stmt = None
            ctx.drop_line()
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
        case "VARIABLE":
            # Asignment to existing variable
            result = do_assignment(ctx)
        case "PROCEDURE":
            if (
                ctx.current_subproc is not None
                and ctx.tok.value.name == ctx.current_subproc.name
                and ctx.current_subproc.signature.ret != TYPE__NONE
            ):
                result = do_set_return(ctx)
            else:
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
    if not ctx.at_line_terminator():
        ctx.diags.raise_error(
            diag.E_UNEXPECTED_ITEM, ctx.tok, ctx.tok.value, "end of statement"
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


def do_set_return(ctx: ParseContext):
    """
    Expects: function name in lvalue position
    """
    lex_start = ctx.tok.lexpos
    next(ctx)
    ctx.consume("PUNCTUATION", "=")
    assert ctx.current_subproc is not None
    return SetReturn(ctx.current_subproc, do_expr(ctx), lex_start=lex_start)


def do_procedure_call(ctx: ParseContext):
    """
    Expects: procedure name
    """
    target = ctx.tok.value
    lex_start = ctx.tok.lexpos
    lex_len = ctx.tok.length
    next(ctx)
    if not ctx.at_line_terminator():
        args = do_func_args(ctx)
        return Call(
            target,
            args,
            lex_start=lex_start,
            lex_len=(ctx.prev.lexpos + ctx.prev.length - lex_start),
        )
    return Call(target, lex_start=lex_start, lex_len=lex_len)
