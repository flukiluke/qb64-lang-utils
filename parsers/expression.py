from ast_nodes import BinOp, Constant, Expr, UniOp
from datatypes import BUILTIN_TYPES
from errors import ParseError
from parsers.context import ParseContext

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


def parse(ctx: ParseContext, right_binding: int = 0) -> Expr:
    """
    Expects: first token of expression
    Results: token after expression
    Note: the expression parser is greedy; it will only stop when it encounters
          a token that cannot possibly be part of an expression.
    """

    def start():
        token = ctx.tok
        next(ctx)
        match token.type, token.value:
            case "PUNCTUATION", "(":
                result = parse(ctx)
                ctx.consume("PUNCTUATION", "(")
                return result
            case "PUNCTUATION", "-":
                return UniOp("negation", parse(ctx, PREC_NEGATION))
            case "KEYWORD", "not":
                return UniOp("not", parse(ctx, PRECEDENCE["not"]))
            case "ID", _:
                raise ParseError("Unimplemented implicit variable declaration")
            case "STRING_LIT", _:
                return Constant(token.value, BUILTIN_TYPES["string"])
            case (("BASE_LIT" | "EXP_LIT" | "DEC_LIT" | "INT_LIT"), _):
                return Constant(token.value, detect_numeric_type(token.value))
            case "PROCEDURE", _:
                raise ParseError("Unimplemented procedure call")
            case "VARIABLE", _:
                raise ParseError("Unimplemented variable access")
            case _:
                raise ParseError(f"Unexpected {token.type} {token.value}")

    def binding_power():
        match ctx.tok.type, ctx.tok.value:
            case (("STRING_LIT" | "BASE_LIT" | "EXP_LIT" | "DEC_LIT" | "INT_LIT"), _):
                raise ParseError("Unexpected literal")
            case "PUNCTUATION", ")":
                return 0
            case (("PUNCTUATION" | "KEYWORD"), op) if op in PRECEDENCE:
                return PRECEDENCE[op]
            case _:
                return 0

    def trailing(left: Expr):
        token = ctx.tok
        next(ctx)
        if token.type in ["KEYWORD", "PUNCTUATION"] and token.value in PRECEDENCE:
            right = parse(ctx, PRECEDENCE[token.value])
            return BinOp(token.value, left, right)
        raise ParseError(f"Unpexpected {token.type} {token.value}")

    left = start()
    while right_binding < binding_power():
        left = trailing(left)
    return left


def detect_numeric_type(number: int | float):
    return BUILTIN_TYPES["single"]
