from .. import diagnostics as diag
from ..ast import Call, Cast, Constant, Expr, Print, Var
from ..datatypes import (
    TYPE__INTEGER64,
    TYPE_INTEGER,
    TYPE_SINGLE,
)
from .helpers import Ast, builtin_proc, check, parse_clean, run_var

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


def test_binop_precedence1():
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


def test_binop_precedence2():
    check(
        "2 and 3 = 4 + 5 / 6",
        Ast(
            Call,
            builtin_proc("and"),
            [
                Ast(Constant, 2),
                Cast(
                    Ast(
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
                    ),
                    TYPE_INTEGER,
                ),
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


def test_not1():
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


def test_not2():
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


def test_not3():
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


def test_parentheses1():
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


def test_parentheses2():
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
    check("2 +", d=diag.E_UNEXPECTED_ITEM)
    check("2 + (3", d=diag.E_UNEXPECTED_ITEM)
    check("2 + .", d=diag.E_UNEXPECTED_ITEM)
    check("2 + (3.", d=diag.E_UNEXPECTED_ITEM)
    check("2)", d=diag.E_UNEXPECTED_ITEM)
    check("2 + * 3", d=diag.E_UNEXPECTED_ITEM)
    check("2 + (*) 3", d=diag.E_UNEXPECTED_ITEM)
    check("2 3", d=diag.E_UNEXPECTED_ITEM)


def test_existing_scalar():
    impl, variable = run_var("x = 10 : ? x + 3", "x")
    expr = impl.find(Print).find(Expr)
    assert expr == Ast(
        Call,
        builtin_proc("+"),
        [Ast(Var, variable), Cast(Ast(Constant, 3), TYPE_SINGLE)],
        INFIX,
    )


def test_implicit_scalar():
    impl, variable = run_var("? x + 3", "x")
    expr = impl.find(Print).find(Expr)
    assert expr == Ast(
        Call,
        builtin_proc("+"),
        [Ast(Var, variable), Cast(Ast(Constant, 3), TYPE_SINGLE)],
        INFIX,
    )


def test_function_call_unary():
    program = parse_clean('? lcase$("hello")')
    proc = program.symbols.find_procedure("lcase$")
    assert proc is not None
    expr = program.main.find(Print).find(Expr)
    assert expr == Ast(Call, proc, [Ast(Constant, "hello")])


def test_unary_function_call_bad_syntax():
    check('lcase$("hello"', d=diag.E_UNEXPECTED_ITEM)
    check('lcase$ "hello"', d=diag.E_UNEXPECTED_ITEM)
    check('lcase$ "hello")', d=diag.E_UNEXPECTED_ITEM)
    check('lcase$("hello",)', d=diag.E_UNEXPECTED_ITEM)


def test_function_call_binary():
    program = parse_clean('? left$("Hello", 23)')
    expr = program.main.find(Print).find(Expr)
    assert expr == Ast(
        Call,
        program.symbols.find_procedure("left$"),
        [
            Ast(Constant, "Hello"),
            Cast(Ast(Constant, 23, TYPE_INTEGER), TYPE__INTEGER64),
        ],
    )


def test_function_call_nested():
    program = parse_clean('? lcase$(lcase$("foo") + "bar")')
    proc = program.symbols.find_procedure("lcase$")
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
