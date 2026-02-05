from .. import diagnostics as diag
from .. import parse
from ..ast import Assignment, Call, Cast, Constant, Var
from ..datatypes import TYPE_SINGLE
from .helpers import Ast, builtin_proc, run_var


def test_implicit_scalar():
    impl, variable = run_var("x = 5", "x")
    assert impl.find(Assignment) == Assignment(
        Ast(Var, variable), Cast(Ast(Constant, 5), TYPE_SINGLE)
    )


def test_existing_scalar():
    impl, variable = run_var("foo = 32 : foo = 17", "foo")
    assert list(impl.find_all(Assignment)) == [
        Assignment(Ast(Var, variable), Cast(Ast(Constant, 32), TYPE_SINGLE)),
        Assignment(Ast(Var, variable), Cast(Ast(Constant, 17), TYPE_SINGLE)),
    ]


def test_expression_rvalue():
    impl, variable = run_var("foo = 23 / 7", "foo")
    assert impl.find(Assignment) == Assignment(
        Ast(Var, variable),
        Ast(
            Call,
            builtin_proc("/"),
            [Cast(Ast(Constant, 23), TYPE_SINGLE), Cast(Ast(Constant, 7), TYPE_SINGLE)],
        ),
    )


def test_type_mismatch():
    assert parse("x$ = 3").diagnostics.has(diag.E_ASSIGNMENT_MISMATCH)
