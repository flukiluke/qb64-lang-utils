from qbparse import parse
from qbparse.ast import Assignment, Call, Cast, Constant, Var
from qbparse.datatypes import TYPE_SINGLE

from .helpers import Ast, builtin_proc


def run(input: str, variable_name: str):
    program = parse(input)
    variable = program.globals.find_variable(variable_name)
    assert variable is not None
    assert variable.name == variable_name
    return (program.main, variable)


def test_implicit_scalar():
    impl, variable = run("x = 5", "x")
    assert impl.find(Assignment) == Assignment(
        Var(variable), Cast(Ast(Constant, 5), TYPE_SINGLE)
    )


def test_existing_scalar():
    impl, variable = run("foo = 32 : foo = 17", "foo")
    assert list(impl.find_all(Assignment)) == [
        Assignment(Var(variable), Cast(Ast(Constant, 32), TYPE_SINGLE)),
        Assignment(Var(variable), Cast(Ast(Constant, 17), TYPE_SINGLE)),
    ]


def test_expression_rvalue():
    impl, variable = run("foo = 23 / 7", "foo")
    assert impl.find(Assignment) == Assignment(
        Var(variable),
        Ast(
            Call,
            builtin_proc("/"),
            [Cast(Ast(Constant, 23), TYPE_SINGLE), Cast(Ast(Constant, 7), TYPE_SINGLE)],
        ),
    )
