from pytest import raises

from qbparse import parse
from qbparse.ast import Call, Constant, Expr, Node, Print, ProcDefinition, Var
from qbparse.datatypes import TYPE_INTEGER, TYPE_STRING, TypeSignature
from qbparse.errors import ParseError
from qbparse.symbols import Procedure

from .helpers import builtin_proc

INFIX = Call.Style.INFIX
PREFIX = Call.Style.PREFIX


def check(input: str, expected: Node):
    expr = parse("?" + input).main.find(Expr)
    assert expr is not None
    assert expr == expected


def test_binop():
    check(
        "2 + 3 - 4",
        Call(
            builtin_proc("-"),
            [
                Call(
                    builtin_proc("+"),
                    [Constant(2, TYPE_INTEGER), Constant(3, TYPE_INTEGER)],
                    INFIX,
                ),
                Constant(4, TYPE_INTEGER),
            ],
            INFIX,
        ),
    )


def test_binop_precedence():
    check(
        "2 - 3 * 4",
        Call(
            builtin_proc("-"),
            [
                Constant(2, TYPE_INTEGER),
                Call(
                    builtin_proc("*"),
                    [Constant(3, TYPE_INTEGER), Constant(4, TYPE_INTEGER)],
                    INFIX,
                ),
            ],
            INFIX,
        ),
    )
    check(
        "2 and 3 = 4 + 5 / 6",
        Call(
            builtin_proc("and"),
            [
                Constant(2, TYPE_INTEGER),
                Call(
                    builtin_proc("="),
                    [
                        Constant(3, TYPE_INTEGER),
                        Call(
                            builtin_proc("+"),
                            [
                                Constant(4, TYPE_INTEGER),
                                Call(
                                    builtin_proc("/"),
                                    [
                                        Constant(5, TYPE_INTEGER),
                                        Constant(6, TYPE_INTEGER),
                                    ],
                                    INFIX,
                                ),
                            ],
                            INFIX,
                        ),
                    ],
                    INFIX,
                ),
            ],
            INFIX,
        ),
    )


def test_negation():
    check(
        "-2 * -3",
        Call(
            builtin_proc("*"),
            [
                Call(builtin_proc("-"), [Constant(2, TYPE_INTEGER)], PREFIX),
                Call(builtin_proc("-"), [Constant(3, TYPE_INTEGER)], PREFIX),
            ],
            INFIX,
        ),
    )
    check(
        "-(2 > 3)",
        Call(
            builtin_proc("-"),
            [
                Call(
                    builtin_proc(">"),
                    [Constant(2, TYPE_INTEGER), Constant(3, TYPE_INTEGER)],
                    INFIX,
                )
            ],
            PREFIX,
        ),
    )
    check(
        "2 <> --4",
        Call(
            builtin_proc("<>"),
            [
                Constant(2, TYPE_INTEGER),
                Call(
                    builtin_proc("-"),
                    [Call(builtin_proc("-"), [Constant(4, TYPE_INTEGER)], PREFIX)],
                    PREFIX,
                ),
            ],
            INFIX,
        ),
    )
    check(
        "2--4",
        Call(
            builtin_proc("-"),
            [
                Constant(2, TYPE_INTEGER),
                Call(builtin_proc("-"), [Constant(4, TYPE_INTEGER)], PREFIX),
            ],
            INFIX,
        ),
    )
    check(
        "-2^3",
        Call(
            builtin_proc("-"),
            [
                Call(
                    builtin_proc("^"),
                    [Constant(2, TYPE_INTEGER), Constant(3, TYPE_INTEGER)],
                    INFIX,
                )
            ],
            PREFIX,
        ),
    )


def test_not():
    check(
        "2 and not 3",
        Call(
            builtin_proc("and"),
            [
                Constant(2, TYPE_INTEGER),
                Call(builtin_proc("not"), [Constant(3, TYPE_INTEGER)], PREFIX),
            ],
            INFIX,
        ),
    )
    check(
        "not 2 + 3",
        Call(
            builtin_proc("not"),
            [
                Call(
                    builtin_proc("+"),
                    [Constant(2, TYPE_INTEGER), Constant(3, TYPE_INTEGER)],
                    INFIX,
                )
            ],
            PREFIX,
        ),
    )
    check(
        "not not 2 and not - not 3",
        Call(
            builtin_proc("and"),
            [
                Call(
                    builtin_proc("not"),
                    [Call(builtin_proc("not"), [Constant(2, TYPE_INTEGER)], PREFIX)],
                    PREFIX,
                ),
                Call(
                    builtin_proc("not"),
                    [
                        Call(
                            builtin_proc("-"),
                            [
                                Call(
                                    builtin_proc("not"),
                                    [Constant(3, TYPE_INTEGER)],
                                    PREFIX,
                                )
                            ],
                            PREFIX,
                        )
                    ],
                    PREFIX,
                ),
            ],
            INFIX,
        ),
    )


def test_parentheses():
    check(
        "(2 - 3) * 4",
        Call(
            builtin_proc("*"),
            [
                Call(
                    builtin_proc("-"),
                    [Constant(2, TYPE_INTEGER), Constant(3, TYPE_INTEGER)],
                    INFIX,
                ),
                Constant(4, TYPE_INTEGER),
            ],
            INFIX,
        ),
    )
    check(
        "-(2 + ((3 or 4) and ((5))))",
        Call(
            builtin_proc("-"),
            [
                Call(
                    builtin_proc("+"),
                    [
                        Constant(2, TYPE_INTEGER),
                        Call(
                            builtin_proc("and"),
                            [
                                Call(
                                    builtin_proc("or"),
                                    [
                                        Constant(3, TYPE_INTEGER),
                                        Constant(4, TYPE_INTEGER),
                                    ],
                                    INFIX,
                                ),
                                Constant(5, TYPE_INTEGER),
                            ],
                            INFIX,
                        ),
                    ],
                    INFIX,
                )
            ],
            PREFIX,
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
    assert expr == Call(
        builtin_proc("+"), [Var(variable), Constant(3, TYPE_INTEGER)], INFIX
    )


def test_implicit_scalar():
    program = parse("? x + 3")
    variable = program.globals.find_variable("x")
    assert variable is not None

    expr = program.main.find(Print).find(Expr)
    assert expr == Call(
        builtin_proc("+"), [Var(variable), Constant(3, TYPE_INTEGER)], INFIX
    )


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
    program.globals.add_procedure(
        Procedure(
            "binfunc",
            [
                ProcDefinition(
                    "binfunc",
                    TypeSignature(TYPE_INTEGER, [TYPE_INTEGER, TYPE_STRING]),
                    [],
                )
            ],
        )
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
            Call(
                builtin_proc("+"),
                [Call(proc, [Constant("foo", TYPE_STRING)]),
                Constant("bar", TYPE_STRING)], INFIX
            )
        ],
    )
