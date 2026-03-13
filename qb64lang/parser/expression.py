from . import diagnostics as diag
from .ast import ArrayAccess, Call, Constant, Expr, FieldAccess, LValue, Var
from .context import ParseContext
from .datatypes import TYPE_STRING, ArrayType, CompoundType, Type
from .lexer import Id

PRECEDENCE = {
    "imp": 2,
    "eqv": 3,
    "xor": 4,
    "or": 5,
    "and": 6,
    "not": 7,
    "=": 8,
    "<>": 8,
    "<": 8,
    ">": 8,
    "<=": 8,
    ">=": 8,
    "+": 9,
    "-": 9,  # Binary subtraction
    "mod": 10,
    "\\": 11,
    "*": 12,
    "/": 12,
    "^": 14,
}
# Precedence of - or + sign on a number
PREC_SIGN = 13


def do_expr(ctx: ParseContext, right_binding: int = 0) -> Expr:
    """
    Expects: first token of expression
    Results: token after expression
    Note: the expression parser is greedy; it will only stop when it encounters
          a token that cannot possibly be part of an expression.
    """

    def start() -> Expr:
        token = ctx.tok
        next(ctx)
        match token.type, token.value:
            case "PUNCTUATION", "(":
                result = do_expr(ctx)
                result.parens += 1
                ctx.consume("PUNCTUATION", ")")
                return result
            case "PUNCTUATION", "-":
                return Call(
                    ctx.symbols.procedures["-"],
                    [do_expr(ctx, PREC_SIGN)],
                    style=Call.Style.PREFIX,
                    lex_start=token.lexpos,
                    lex_end=ctx.prev.lexend,
                )
            case "PUNCTUATION", "+":
                return Call(
                    ctx.symbols.procedures["+"],
                    [do_expr(ctx, PREC_SIGN)],
                    style=Call.Style.PREFIX,
                    lex_start=token.lexpos,
                    lex_end=ctx.prev.lexend,
                )
            case "KEYWORD", "not":
                return Call(
                    ctx.symbols.procedures["not"],
                    [do_expr(ctx, PRECEDENCE["not"])],
                    style=Call.Style.PREFIX,
                    lex_start=token.lexpos,
                    lex_end=ctx.prev.lexend,
                )
            case "ID", _:
                ctx.reverse()
                return do_lvalue(ctx)
            case "STRING_LIT", _:
                return Constant(
                    token.value,
                    TYPE_STRING,
                    lex_start=token.lexpos,
                    lex_end=token.lexend,
                )
            case "NUM_LIT", _:
                return Constant(
                    token.value.value,
                    token.value.type,
                    lex_start=token.lexpos,
                    lex_end=token.lexend,
                )
            case "PROCEDURE", _:
                ctx.reverse()
                return do_func_call(ctx)
            case "VARIABLE", _:
                ctx.reverse()
                return do_lvalue(ctx)
            case _:
                ctx.diags.raise_error(
                    diag.E_UNEXPECTED_ITEM, token, token.value, "an expression"
                )

    def binding_power():
        match ctx.tok.type, ctx.tok.value:
            case (("PUNCTUATION" | "KEYWORD"), op) if op in PRECEDENCE:
                return PRECEDENCE[op]
            case _:
                return 0

    def trailing(left: Expr):
        token = ctx.tok
        next(ctx)
        right = do_expr(ctx, PRECEDENCE[token.value])
        return Call(
            ctx.symbols.procedures[token.value],
            [left, right],
            style=Call.Style.INFIX,
            lex_start=token.lexpos,
            lex_end=ctx.prev.lexend,
        )

    left = start()
    while right_binding < binding_power():
        left = trailing(left)
    return left


def do_lvalue(ctx: ParseContext) -> LValue:
    def field_access(base: LValue, type: Type):
        if not isinstance(type, CompoundType):
            ctx.diags.raise_error(
                diag.E_FIELD_ACCESS_NON_COMPOUND,
                ctx.tok,
                ctx.tok.plain_value,
                type.source_name,
            )
        field = type.get_field(ctx.tok.value)
        if not field:
            ctx.diags.raise_error(
                diag.E_UNKNOWN_FIELD, ctx.tok, ctx.tok.plain_value, type.source_name
            )
        next(ctx)
        type = field.type
        result = FieldAccess(
            base, field, lex_start=ctx.prev.lexpos, lex_end=ctx.prev.lexend
        )
        return (result, type)

    def array_access(base: LValue, type: Type):
        if not isinstance(type, ArrayType):
            ctx.diags.raise_error(
                diag.E_ARRAY_ACCESS_NON_ARRAY, ctx.tok, type.source_name
            )
        lex_start = ctx.tok.lexpos
        indices = list[Expr]()
        ctx.consume("PUNCTUATION", "(")
        while True:
            indices.append(do_expr(ctx))
            if ctx.at_a("PUNCTUATION", ","):
                next(ctx)
            else:
                break
        ctx.consume("PUNCTUATION", ")")
        result = ArrayAccess(
            base, indices, lex_start=lex_start, lex_end=ctx.prev.lexpos
        )
        type = type.element_type
        return (result, type)

    result = do_bare_var(ctx)
    type = result.target.type
    while ctx.at_a("DOTTED_ID") or ctx.at_a("PUNCTUATION", "("):
        if ctx.at_a("DOTTED_ID"):
            result, type = field_access(result, type)
        else:
            result, type = array_access(result, type)
    return result


def do_bare_var(ctx: ParseContext) -> Var:
    """
    A variable with no compound field access or array indexing
    """
    if ctx.tok.type == "VARIABLE":
        result = Var(ctx.tok.value, lex_start=ctx.tok.lexpos, lex_end=ctx.tok.lexend)
    elif ctx.tok.type == "ID":
        var_id: Id = ctx.tok.value
        result = Var(
            ctx.symbols.create_local(var_id.name, ctx.tok.plain_value, var_id.type),
            lex_start=ctx.tok.lexpos,
            lex_end=ctx.tok.lexend,
        )
    else:
        ctx.diags.raise_error(diag.E_EXPECTED_VAR_NAME, ctx.tok)
    next(ctx)
    return result


def do_func_call(ctx: ParseContext) -> Call:
    """
    Expects: name of function
    Results: token after )
    Format: name [(args)]
    """
    target = ctx.tok.value
    lex_start, lex_end = ctx.tok.lexpos, ctx.tok.lexend
    next(ctx)
    if ctx.at_a("PUNCTUATION", "("):
        next(ctx)
        args = do_func_args(ctx)
        ctx.consume("PUNCTUATION", ")")
        return Call(target, args, lex_start=lex_start, lex_end=ctx.prev.lexend)
    return Call(target, lex_start=lex_start, lex_end=lex_end)


def do_func_args(ctx: ParseContext) -> list[Expr]:
    """
    Expects: start of first argument
    Results: token after last argument
    Format: comma-separated arguments
    """
    args = list[Expr]()
    while True:
        args.append(do_expr(ctx))
        if ctx.at_a("PUNCTUATION", ","):
            next(ctx)
        else:
            return args
