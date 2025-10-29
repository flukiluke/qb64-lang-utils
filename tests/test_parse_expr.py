from pytest import raises

import ast_nodes as ast
from datatypes import BUILTIN_TYPES
from errors import ParseError
from parsers import parse

SINGLE = BUILTIN_TYPES["single"]


def check(input: str, expected: ast.Node):
    expr = parse("?" + input).procedures["_main"].find(ast.Expr)
    assert expr is not None
    assert expr == expected


def test_binop():
    check(
        "2 + 3 - 4",
        ast.BinOp(
            "-",
            ast.BinOp("+", ast.Constant(2, SINGLE), ast.Constant(3, SINGLE)),
            ast.Constant(4, SINGLE),
        ),
    )


def test_binop_precedence():
    check(
        "2 - 3 * 4",
        ast.BinOp(
            "-",
            ast.Constant(2, SINGLE),
            ast.BinOp("*", ast.Constant(3, SINGLE), ast.Constant(4, SINGLE)),
        ),
    )
    check(
        "2 and 3 = 4 + 5 / 6",
        ast.BinOp(
            "and",
            ast.Constant(2, SINGLE),
            ast.BinOp(
                "=",
                ast.Constant(3, SINGLE),
                ast.BinOp(
                    "+",
                    ast.Constant(4, SINGLE),
                    ast.BinOp("/", ast.Constant(5, SINGLE), ast.Constant(6, SINGLE)),
                ),
            ),
        ),
    )


def test_negation():
    check(
        "-2 * -3",
        ast.BinOp(
            "*",
            ast.UniOp("negation", ast.Constant(2, SINGLE)),
            ast.UniOp("negation", ast.Constant(3, SINGLE)),
        ),
    )
    check(
        "-(2 > 3)",
        ast.UniOp(
            "negation",
            ast.BinOp(">", ast.Constant(2, SINGLE), ast.Constant(3, SINGLE)),
        ),
    )
    check(
        "2 <> --4",
        ast.BinOp(
            "<>",
            ast.Constant(2, SINGLE),
            ast.UniOp("negation", ast.UniOp("negation", ast.Constant(4, SINGLE))),
        ),
    )
    check(
        "2--4",
        ast.BinOp(
            "-",
            ast.Constant(2, SINGLE),
            ast.UniOp("negation", ast.Constant(4, SINGLE)),
        ),
    )
    check(
        "-2^3",
        ast.UniOp(
            "negation", ast.BinOp("^", ast.Constant(2, SINGLE), ast.Constant(3, SINGLE))
        ),
    )


def test_not():
    check(
        "2 and not 3",
        ast.BinOp(
            "and", ast.Constant(2, SINGLE), ast.UniOp("not", ast.Constant(3, SINGLE))
        ),
    )
    check(
        "not 2 + 3",
        ast.UniOp(
            "not", ast.BinOp("+", ast.Constant(2, SINGLE), ast.Constant(3, SINGLE))
        ),
    )
    check(
        "not not 2 and not - not 3",
        ast.BinOp(
            "and",
            ast.UniOp("not", ast.UniOp("not", ast.Constant(2, SINGLE))),
            ast.UniOp(
                "not", ast.UniOp("negation", ast.UniOp("not", ast.Constant(3, SINGLE)))
            ),
        ),
    )


def test_parentheses():
    check(
        "(2 - 3) * 4",
        ast.BinOp(
            "*",
            ast.BinOp("-", ast.Constant(2, SINGLE), ast.Constant(3, SINGLE)),
            ast.Constant(4, SINGLE),
        ),
    )
    check(
        "-(2 + ((3 or 4) and ((5))))",
        ast.UniOp(
            "negation",
            ast.BinOp(
                "+",
                ast.Constant(2, SINGLE),
                ast.BinOp(
                    "and",
                    ast.BinOp("or", ast.Constant(3, SINGLE), ast.Constant(4, SINGLE)),
                    ast.Constant(5, SINGLE),
                ),
            ),
        ),
    )


def test_errors():
    raises(ParseError, parse, "? 2 +")
    raises(ParseError, parse, "? 2 + (3")
    raises(ParseError, parse, "? 2 + .")
    raises(ParseError, parse, "? 2 + (3.")
    raises(ParseError, parse, "? 2)")
    raises(ParseError, parse, "? 2 + * 3")
    raises(ParseError, parse, "? 2 + (*) 3")
