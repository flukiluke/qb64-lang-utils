from pytest import raises

from qbparse import parse
from qbparse.ast import BinOp, Constant, Expr, Node, Print, UniOp, Var
from qbparse.datatypes import BUILTIN_TYPES
from qbparse.errors import ParseError

SINGLE = BUILTIN_TYPES["single"]


def check(input: str, expected: Node):
    impl = parse("?" + input).globals.procedures["_main"].impl
    assert impl is not None
    expr = impl.find(Expr)
    assert expr is not None
    assert expr == expected


def test_binop():
    check(
        "2 + 3 - 4",
        BinOp(
            "-",
            BinOp("+", Constant(2, SINGLE), Constant(3, SINGLE)),
            Constant(4, SINGLE),
        ),
    )


def test_binop_precedence():
    check(
        "2 - 3 * 4",
        BinOp(
            "-",
            Constant(2, SINGLE),
            BinOp("*", Constant(3, SINGLE), Constant(4, SINGLE)),
        ),
    )
    check(
        "2 and 3 = 4 + 5 / 6",
        BinOp(
            "and",
            Constant(2, SINGLE),
            BinOp(
                "=",
                Constant(3, SINGLE),
                BinOp(
                    "+",
                    Constant(4, SINGLE),
                    BinOp("/", Constant(5, SINGLE), Constant(6, SINGLE)),
                ),
            ),
        ),
    )


def test_negation():
    check(
        "-2 * -3",
        BinOp(
            "*",
            UniOp("negation", Constant(2, SINGLE)),
            UniOp("negation", Constant(3, SINGLE)),
        ),
    )
    check(
        "-(2 > 3)",
        UniOp(
            "negation",
            BinOp(">", Constant(2, SINGLE), Constant(3, SINGLE)),
        ),
    )
    check(
        "2 <> --4",
        BinOp(
            "<>",
            Constant(2, SINGLE),
            UniOp("negation", UniOp("negation", Constant(4, SINGLE))),
        ),
    )
    check(
        "2--4",
        BinOp(
            "-",
            Constant(2, SINGLE),
            UniOp("negation", Constant(4, SINGLE)),
        ),
    )
    check(
        "-2^3",
        UniOp("negation", BinOp("^", Constant(2, SINGLE), Constant(3, SINGLE))),
    )


def test_not():
    check(
        "2 and not 3",
        BinOp("and", Constant(2, SINGLE), UniOp("not", Constant(3, SINGLE))),
    )
    check(
        "not 2 + 3",
        UniOp("not", BinOp("+", Constant(2, SINGLE), Constant(3, SINGLE))),
    )
    check(
        "not not 2 and not - not 3",
        BinOp(
            "and",
            UniOp("not", UniOp("not", Constant(2, SINGLE))),
            UniOp("not", UniOp("negation", UniOp("not", Constant(3, SINGLE)))),
        ),
    )


def test_parentheses():
    check(
        "(2 - 3) * 4",
        BinOp(
            "*",
            BinOp("-", Constant(2, SINGLE), Constant(3, SINGLE)),
            Constant(4, SINGLE),
        ),
    )
    check(
        "-(2 + ((3 or 4) and ((5))))",
        UniOp(
            "negation",
            BinOp(
                "+",
                Constant(2, SINGLE),
                BinOp(
                    "and",
                    BinOp("or", Constant(3, SINGLE), Constant(4, SINGLE)),
                    Constant(5, SINGLE),
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


def test_existing_scalar():
    program = parse("x = 10 : ? x + 3")
    variable = program.globals.find_variable("x")
    impl = program.globals.procedures["_main"].impl
    assert variable is not None
    assert impl is not None

    expr = impl.find(Print).find(Expr)
    assert expr == BinOp("+", Var(variable), Constant(3, SINGLE))


def test_implicit_scalar():
    program = parse("? x + 3")
    variable = program.globals.find_variable("x")
    impl = program.globals.procedures["_main"].impl
    assert variable is not None
    assert impl is not None

    expr = impl.find(Print).find(Expr)
    assert expr == BinOp("+", Var(variable), Constant(3, SINGLE))

