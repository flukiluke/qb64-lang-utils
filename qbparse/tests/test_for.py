import qbparse.diagnostics as diag
from qbparse import parse
from qbparse.ast import Cast, Constant, Expr, For, Print, Var
from qbparse.datatypes import TYPE_SINGLE
from qbparse.tests.helpers import Ast, run_var


def test_explicit_next():
    impl, var = run_var(
        """
        for i = 1! to 10!
            print i
        next i""",
        "i",
    )
    assert impl.find(For) == Ast(
        For,
        Ast(Var, var),
        Ast(Constant, 1),
        Ast(Constant, 10),
        Ast(Constant, 1),
        [Ast(Print)],
    )


def test_implicit_next():
    impl, var = run_var(
        """
        for i = 1! to 10!
            print i
        next""",
        "i",
    )
    assert impl.find(For) == Ast(
        For,
        Ast(Var, var),
        Ast(Constant, 1),
        Ast(Constant, 10),
        Ast(Constant, 1),
        [Ast(Print)],
    )


def test_nested_for():
    impl, var = run_var(
        """
        for i = 1! to 10!
            for j = 1! to 8!
                print i
            next j
        next i""",
        "i",
    )
    assert impl.find(For) == Ast(
        For,
        Ast(Var, var),
        Ast(Constant, 1),
        Ast(Constant, 10),
        Ast(Constant, 1),
        [
            Ast(
                For,
                Ast(Var),
                Ast(Constant, 1),
                Ast(Constant, 8),
                Ast(Constant, 1),
                [Ast(Print)],
            )
        ],
    )


def test_merged_next():
    impl, var = run_var(
        """
        for i = 1! to 10!
            for j = 1! to 8!
                for k = 1! to 1!
                print i
            next k, j, i""",
        "i",
    )
    assert impl.find(For) == Ast(
        For,
        Ast(Var, var),
        Ast(Constant, 1),
        Ast(Constant, 10),
        Ast(Constant, 1),
        [
            Ast(
                For,
                Ast(Var),
                Ast(Constant, 1),
                Ast(Constant, 8),
                Ast(Constant, 1),
                [Ast(For)],
            )
        ],
    )


def test_step():
    impl, var = run_var(
        """
        for i = 1! to 10! step 3!
            print i
        next i""",
        "i",
    )
    assert impl.find(For) == Ast(
        For,
        Ast(Var, var),
        Ast(Constant, 1),
        Ast(Constant, 10),
        Ast(Constant, 3),
        [Ast(Print)],
    )


def test_expr():
    impl, var = run_var(
        """
        for i = x * 2 to x * 3 step x / 1
            print i
        next i""",
        "i",
    )
    assert impl.find(For) == Ast(
        For,
        Ast(Var, var),
        Ast(Expr),
        Ast(Expr),
        Ast(Expr),
        [Ast(Print)],
    )


def test_missing_parts():
    assert parse("for").diagnostics.has(diag.E_EXPECTED_VAR_NAME)
    assert parse("for i 1 to 10").diagnostics.has(diag.E_UNEXPECTED_ITEM)
    assert parse("for i = 1 to").diagnostics.has(diag.E_UNEXPECTED_ITEM)
    assert parse("for i = 1 to 10 step 3 : ? 3").diagnostics.has(diag.E_UNEXPECTED_ITEM)


def test_missing_newline():
    assert parse("for i = 1 to 10 ? 3\nnext i").diagnostics.has(diag.E_UNEXPECTED_ITEM)
    assert parse("for i = 1 to 10 step 2 ? 3\nnext i").diagnostics.has(
        diag.E_UNEXPECTED_ITEM
    )
    assert parse("for i = 1 to 10 step 2 \nnext i ? 3").diagnostics.has(
        diag.E_UNEXPECTED_ITEM
    )


def test_bad_var():
    assert parse("for = 1 to 10 : next i").diagnostics.has(diag.E_EXPECTED_VAR_NAME)
    assert parse("for 2 = 1 to 10 : next i").diagnostics.has(diag.E_EXPECTED_VAR_NAME)


def test_non_numerics():
    assert parse("for x$ = 1 to 10 : next x$").diagnostics.has(
        diag.E_NON_NUMERIC_VARIABLE
    )
    assert parse('for x = "a" to 10 : next x').diagnostics.has(diag.E_NON_NUMERIC_EXPR)
    assert parse('for x = 1 to "a" : next x').diagnostics.has(diag.E_NON_NUMERIC_EXPR)
    assert parse('for x = 1 to 10 step "a" : next x').diagnostics.has(
        diag.E_NON_NUMERIC_EXPR
    )


def test_casts():
    impl, var = run_var("for i = 1& to 10% step 3# : next i", "i")
    assert impl.find(For) == Ast(
        For,
        Ast(Var, var),
        Cast(Ast(Constant, 1), TYPE_SINGLE),
        Cast(Ast(Constant, 10), TYPE_SINGLE),
        Cast(Ast(Constant, 3), TYPE_SINGLE),
    )
