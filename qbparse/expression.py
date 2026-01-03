import qbparse.diagnostics as diag
from qbparse.ast import Call, Constant, Expr, LValue, Var
from qbparse.context import ParseContext
from qbparse.datatypes import TYPE_STRING

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
PREC_NEGATION = 13


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
                ctx.consume("PUNCTUATION", ")")
                return result
            case "PUNCTUATION", "-":
                return Call(
                    ctx.symbols.procedures["-"],
                    [do_expr(ctx, PREC_NEGATION)],
                    style=Call.Style.PREFIX,
                )
            case "KEYWORD", "not":
                return Call(
                    ctx.symbols.procedures["not"],
                    [do_expr(ctx, PRECEDENCE["not"])],
                    style=Call.Style.PREFIX,
                )
            case "ID", _:
                ctx.reverse()
                return do_lvalue(ctx)
            case "STRING_LIT", _:
                return Constant(token.value, TYPE_STRING)
            case "NUM_LIT", _:
                return Constant(token.value[0], token.value[1])
            case "PROCEDURE", _:
                ctx.reverse()
                return do_func_call(ctx)
            case "VARIABLE", var:
                return Var(var)
            case _:
                ctx.diags.raise_error(
                    diag.E_UNEXPECTED_ITEM, token, token.value, "an expression"
                )

    def binding_power():
        match ctx.tok.type, ctx.tok.value:
            case ("STRING_LIT", _):
                ctx.diags.raise_error(
                    diag.E_UNEXPECTED_ITEM,
                    ctx.tok,
                    '"' + ctx.tok.value + '"',
                    "an operator",
                )
            case ("NUM_LIT", _):
                ctx.diags.raise_error(
                    diag.E_UNEXPECTED_ITEM, ctx.tok, ctx.tok.value[0], "an operator"
                )
            case "PUNCTUATION", ")":
                return 0
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
        )

    left = start()
    while right_binding < binding_power():
        left = trailing(left)
    return left


def do_lvalue(ctx: ParseContext) -> LValue:
    if ctx.tok.type == "VARIABLE":
        result = Var(ctx.tok.value)
    elif ctx.tok.type == "ID":
        result = Var(ctx.symbols.create_local(*ctx.tok.value))
    else:
        assert False, "LValue with non variable or ID"
    next(ctx)
    return result


def do_func_call(ctx: ParseContext) -> Call:
    """
    Expects: name of function
    Results: token after )
    Format: name [(args)]
    """
    target = ctx.tok.value
    next(ctx)
    if ctx.at_a("PUNCTUATION", "("):
        next(ctx)
        args = do_func_args(ctx)
        ctx.consume("PUNCTUATION", ")")
        return Call(target, args)
    return Call(target)


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
