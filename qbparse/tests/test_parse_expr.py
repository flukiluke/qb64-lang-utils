from pytest import raises

from qbparse import parse
from qbparse.ast import Call, Cast, Constant, Expr, Print, Var
from qbparse.datatypes import (
    TYPE__INTEGER64,
    TYPE_INTEGER,
    TYPE_SINGLE,
)

from .helpers import Ast, builtin_proc, check

INFIX = Call.Style.INFIX
PREFIX = Call.Style.PREFIX


def test_binop():
    check(
        "2 + 3 - 4",
        Ast(
            Call,
            builtin_proc("-"),
            [
                Ast(
                    Call,
                    builtin_proc("+"),
                    [Ast(Constant, 2), Ast(Constant, 3)],
                    INFIX,
                ),
                Ast(Constant, 4),
            ],
            INFIX,
        ),
    )


def test_binop_precedence():
    check(
        "2 - 3 * 4",
        Ast(
            Call,
            builtin_proc("-"),
            [
                Ast(Constant, 2),
                Ast(
                    Call,
                    builtin_proc("*"),
                    [Ast(Constant, 3), Ast(Constant, 4)],
                    INFIX,
                ),
            ],
            INFIX,
        ),
    )
    check(
        "2 and 3 = 4 + 5 / 6",
        Ast(
            Call,
            builtin_proc("and"),
            [
                Ast(Constant, 2),
                Cast(Ast(
                    Call,
                    builtin_proc("="),
                    [
                        Cast(Ast(Constant, 3), TYPE_SINGLE),
                        Ast(
                            Call,
                            builtin_proc("+"),
                            [
                                Cast(Ast(Constant, 4), TYPE_SINGLE),
                                Ast(
                                    Call,
                                    builtin_proc("/"),
                                    [
                                        Cast(Ast(Constant, 5), TYPE_SINGLE),
                                        Cast(Ast(Constant, 6), TYPE_SINGLE),
                                    ],
                                    INFIX,
                                ),
                            ],
                            INFIX,
                        ),
                    ],
                    INFIX,
                ), TYPE_INTEGER)
            ],
            INFIX,
        ),
    )


def test_negation():
    check(
        "-2 * -3",
        Ast(
            Call,
            builtin_proc("*"),
            [
                Ast(Call, builtin_proc("-"), [Ast(Constant, 2)], PREFIX),
                Ast(Call, builtin_proc("-"), [Ast(Constant, 3)], PREFIX),
            ],
            INFIX,
        ),
    )
    check(
        "-(2 > 3)",
        Ast(
            Call,
            builtin_proc("-"),
            [
                Ast(
                    Call,
                    builtin_proc(">"),
                    [Ast(Constant, 2), Ast(Constant, 3)],
                    INFIX,
                )
            ],
            PREFIX,
        ),
    )
    check(
        "2 <> --4",
        Ast(
            Call,
            builtin_proc("<>"),
            [
                Ast(Constant, 2),
                Ast(
                    Call,
                    builtin_proc("-"),
                    [Ast(Call, builtin_proc("-"), [Ast(Constant, 4)], PREFIX)],
                    PREFIX,
                ),
            ],
            INFIX,
        ),
    )
    check(
        "2--4",
        Ast(
            Call,
            builtin_proc("-"),
            [
                Ast(Constant, 2),
                Ast(Call, builtin_proc("-"), [Ast(Constant, 4)], PREFIX),
            ],
            INFIX,
        ),
    )
    check(
        "-2^3",
        Ast(
            Call,
            builtin_proc("-"),
            [
                Ast(
                    Call,
                    builtin_proc("^"),
                    [
                        Cast(Ast(Constant, 2), TYPE_SINGLE),
                        Cast(Ast(Constant, 3), TYPE_SINGLE),
                    ],
                    INFIX,
                )
            ],
            PREFIX,
        ),
    )


def test_not():
    check(
        "2 and not 3",
        Ast(
            Call,
            builtin_proc("and"),
            [
                Ast(Constant, 2),
                Ast(Call, builtin_proc("not"), [Ast(Constant, 3)], PREFIX),
            ],
            INFIX,
        ),
    )
    check(
        "not 2 + 3",
        Ast(
            Call,
            builtin_proc("not"),
            [
                Ast(
                    Call,
                    builtin_proc("+"),
                    [Ast(Constant, 2), Ast(Constant, 3)],
                    INFIX,
                )
            ],
            PREFIX,
        ),
    )
    check(
        "not not 2 and not - not 3",
        Ast(
            Call,
            builtin_proc("and"),
            [
                Ast(
                    Call,
                    builtin_proc("not"),
                    [Ast(Call, builtin_proc("not"), [Ast(Constant, 2)], PREFIX)],
                    PREFIX,
                ),
                Ast(
                    Call,
                    builtin_proc("not"),
                    [
                        Ast(
                            Call,
                            builtin_proc("-"),
                            [
                                Ast(
                                    Call,
                                    builtin_proc("not"),
                                    [Ast(Constant, 3)],
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
        Ast(
            Call,
            builtin_proc("*"),
            [
                Ast(
                    Call,
                    builtin_proc("-"),
                    [Ast(Constant, 2), Ast(Constant, 3)],
                    INFIX,
                ),
                Ast(Constant, 4),
            ],
            INFIX,
        ),
    )
    check(
        "-(2 + ((3 or 4) and ((5))))",
        Ast(
            Call,
            builtin_proc("-"),
            [
                Ast(
                    Call,
                    builtin_proc("+"),
                    [
                        Ast(Constant, 2),
                        Ast(
                            Call,
                            builtin_proc("and"),
                            [
                                Ast(
                                    Call,
                                    builtin_proc("or"),
                                    [
                                        Ast(Constant, 3),
                                        Ast(Constant, 4),
                                    ],
                                    INFIX,
                                ),
                                Ast(Constant, 5),
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
    assert expr == Ast(
        Call,
        builtin_proc("+"),
        [Ast(Var, variable), Cast(Ast(Constant, 3), TYPE_SINGLE)],
        INFIX,
    )


def test_implicit_scalar():
    program = parse("? x + 3")
    variable = program.globals.find_variable("x")
    assert variable is not None

    expr = program.main.find(Print).find(Expr)
    assert expr == Ast(
        Call,
        builtin_proc("+"),
        [Ast(Var, variable), Cast(Ast(Constant, 3), TYPE_SINGLE)],
        INFIX,
    )


def test_function_call_unary():
    program = parse('? lcase$("hello")')
    proc = program.globals.find_procedure("lcase$")
    assert proc is not None
    expr = program.main.find(Print).find(Expr)
    assert expr == Ast(Call, proc, [Ast(Constant, "hello")])


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
                UserProcDefinition(
                    "binfunc",
                    TypeSignature(TYPE_INTEGER, [TYPE_INTEGER, TYPE_STRING]),
                    [],
                )
            ],
        )
    )
    program.add_parse('? binfunc(23, "hello")')
    expr = program.main.find(Print).find(Expr)
    assert expr == Ast(
        Call,
        program.globals.procedures["binfunc"],
        [Ast(Constant, 23, TYPE_INTEGER), Ast(Constant, "hello")],
    )


def test_function_call_nested():
    program = parse('? lcase$(lcase$("foo") + "bar")')
    proc = program.globals.find_procedure("lcase$")
    assert proc is not None
    expr = program.main.find(Print).find(Expr)
    assert expr == Ast(
        Call,
        proc,
        [
            Ast(
                Call,
                builtin_proc("+"),
                [
                    Ast(Call, proc, [Ast(Constant, "foo")]),
                    Ast(Constant, "bar"),
                ],
                INFIX,
            )
        ],
    )
