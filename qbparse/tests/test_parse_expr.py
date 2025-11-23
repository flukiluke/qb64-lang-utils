from pytest import raises

from qbparse import parse
from qbparse.ast import BinOp, Call, Constant, Expr, Node, Print, UniOp, Var
from qbparse.datatypes import TYPE_INTEGER, TYPE_STRING, TypeSignature
from qbparse.errors import ParseError
from qbparse.symbols import Procedure


def check(input: str, expected: Node):
    expr = parse("?" + input).main.find(Expr)
    assert expr is not None
    assert expr == expected


def test_binop():
    check(
        "2 + 3 - 4",
        BinOp(
            "-",
            BinOp("+", Constant(2, TYPE_INTEGER), Constant(3, TYPE_INTEGER)),
            Constant(4, TYPE_INTEGER),
        ),
    )


def test_binop_precedence():
    check(
        "2 - 3 * 4",
        BinOp(
            "-",
            Constant(2, TYPE_INTEGER),
            BinOp("*", Constant(3, TYPE_INTEGER), Constant(4, TYPE_INTEGER)),
        ),
    )
    check(
        "2 and 3 = 4 + 5 / 6",
        BinOp(
            "and",
            Constant(2, TYPE_INTEGER),
            BinOp(
                "=",
                Constant(3, TYPE_INTEGER),
                BinOp(
                    "+",
                    Constant(4, TYPE_INTEGER),
                    BinOp("/", Constant(5, TYPE_INTEGER), Constant(6, TYPE_INTEGER)),
                ),
            ),
        ),
    )


def test_negation():
    check(
        "-2 * -3",
        BinOp(
            "*",
            UniOp("negation", Constant(2, TYPE_INTEGER)),
            UniOp("negation", Constant(3, TYPE_INTEGER)),
        ),
    )
    check(
        "-(2 > 3)",
        UniOp(
            "negation",
            BinOp(">", Constant(2, TYPE_INTEGER), Constant(3, TYPE_INTEGER)),
        ),
    )
    check(
        "2 <> --4",
        BinOp(
            "<>",
            Constant(2, TYPE_INTEGER),
            UniOp("negation", UniOp("negation", Constant(4, TYPE_INTEGER))),
        ),
    )
    check(
        "2--4",
        BinOp(
            "-",
            Constant(2, TYPE_INTEGER),
            UniOp("negation", Constant(4, TYPE_INTEGER)),
        ),
    )
    check(
        "-2^3",
        UniOp(
            "negation", BinOp("^", Constant(2, TYPE_INTEGER), Constant(3, TYPE_INTEGER))
        ),
    )


def test_not():
    check(
        "2 and not 3",
        BinOp(
            "and", Constant(2, TYPE_INTEGER), UniOp("not", Constant(3, TYPE_INTEGER))
        ),
    )
    check(
        "not 2 + 3",
        UniOp("not", BinOp("+", Constant(2, TYPE_INTEGER), Constant(3, TYPE_INTEGER))),
    )
    check(
        "not not 2 and not - not 3",
        BinOp(
            "and",
            UniOp("not", UniOp("not", Constant(2, TYPE_INTEGER))),
            UniOp("not", UniOp("negation", UniOp("not", Constant(3, TYPE_INTEGER)))),
        ),
    )


def test_parentheses():
    check(
        "(2 - 3) * 4",
        BinOp(
            "*",
            BinOp("-", Constant(2, TYPE_INTEGER), Constant(3, TYPE_INTEGER)),
            Constant(4, TYPE_INTEGER),
        ),
    )
    check(
        "-(2 + ((3 or 4) and ((5))))",
        UniOp(
            "negation",
            BinOp(
                "+",
                Constant(2, TYPE_INTEGER),
                BinOp(
                    "and",
                    BinOp("or", Constant(3, TYPE_INTEGER), Constant(4, TYPE_INTEGER)),
                    Constant(5, TYPE_INTEGER),
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
    assert variable is not None

    expr = program.main.find(Print).find(Expr)
    assert expr == BinOp("+", Var(variable), Constant(3, TYPE_INTEGER))


def test_implicit_scalar():
    program = parse("? x + 3")
    variable = program.globals.find_variable("x")
    assert variable is not None

    expr = program.main.find(Print).find(Expr)
    assert expr == BinOp("+", Var(variable), Constant(3, TYPE_INTEGER))


def test_function_call_unary():
    program = parse('? lcase$("hello")')
    proc = program.globals.find_procedure("lcase$")
    assert proc is not None
    expr = program.main.find(Print).find(Expr)
    assert expr == Call(proc, [Constant("hello", TYPE_STRING)])


def test_unary_function_call_bad_syntax():
    raises(ParseError, parse, '? lcase$("hello"')
    raises(ParseError, parse, '? lcase$ "hello"')
    raises(ParseError, parse, '? lcase$ "hello")')
    raises(ParseError, parse, '? lcase$ ("hello",)')


def test_function_call_binary():
    program = parse("")
    program.globals.procedures["binfunc"] = Procedure(
        "binfunc", TypeSignature(TYPE_INTEGER, [TYPE_INTEGER, TYPE_STRING])
    )
    program.add_parse('? binfunc(23, "hello")')
    expr = program.main.find(Print).find(Expr)
    assert expr == Call(
        program.globals.procedures["binfunc"],
        [Constant(23, TYPE_INTEGER), Constant("hello", TYPE_STRING)],
    )


def test_function_call_nested():
    program = parse('? lcase$(lcase$("foo") + "bar")')
    proc = program.globals.find_procedure("lcase$")
    assert proc is not None
    expr = program.main.find(Print).find(Expr)
    assert expr == Call(
        proc,
        [
            BinOp(
                "+",
                Call(proc, [Constant("foo", TYPE_STRING)]),
                Constant("bar", TYPE_STRING),
            )
        ],
    )
