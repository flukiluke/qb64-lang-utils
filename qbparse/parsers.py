from qbparse.ast import Assignment, LValue, LVar, Print, Statement
from qbparse.context import ParseContext
from qbparse.errors import ParseError
from qbparse.expression import do_expr


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
        match ctx.tok.type:
            case "COMMA":
                result.params.append(Print.TAB_SEPARATOR)
                final_newline = False
            case "SEMICOLON":
                final_newline = False
            case _:
                result.params.append(do_expr(ctx))
                final_newline = True
    if final_newline:
        result.params.append(Print.FINAL_NEWLINE)
    return result


KEYWORD_PARSERS = {
    "print": do_print,
    "?": do_print,
}


def do_assignment(ctx: ParseContext, lval: LValue | None = None):
    """
    Expects: first token of lvalue if lval == None else "=" token
    Results: token after rvalue
    """
    lval = do_lvalue(ctx)
    ctx.consume("PUNCTUATION", "=")
    rval = do_expr(ctx)
    return Assignment(lval, rval)


def do_lvalue(ctx: ParseContext) -> LValue:
    if ctx.tok.type == "VARIABLE":
        result = LVar(ctx.tok.value)
    elif ctx.tok.type == "ID":
        result = LVar(ctx.symbols.create_local(*ctx.tok.value))
    else:
        raise ParseError(f"Unexpected {ctx.tok.type} {ctx.tok.value}")
    next(ctx)
    return result


def do_procedure_call(ctx: ParseContext):
    pass


def do_stmt(ctx: ParseContext) -> Statement | None:
    result = None
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
    ctx.skip("NEWLINE", "LINE_SPLIT")
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
