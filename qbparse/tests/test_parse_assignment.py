from qbparse import parse
from qbparse.ast import Assignment, BinOp, Constant, Var
from qbparse.datatypes import TYPE_INTEGER


def run(input: str, variable_name: str):
    program = parse(input)
    variable = program.globals.find_variable(variable_name)
    assert variable is not None
    assert variable.name == variable_name
    return (program.main, variable)


def test_implicit_scalar():
    impl, variable = run("x = 5", "x")
    assert impl.find(Assignment) == Assignment(Var(variable), Constant(5, TYPE_INTEGER))


def test_existing_scalar():
    impl, variable = run("foo = 32 : foo = 17", "foo")
    assert list(impl.find_all(Assignment)) == [
        Assignment(Var(variable), Constant(32, TYPE_INTEGER)),
        Assignment(Var(variable), Constant(17, TYPE_INTEGER)),
    ]


def test_expression_rvalue():
    impl, variable = run("foo = 23 / 7", "foo")
    assert impl.find(Assignment) == Assignment(
        Var(variable),
        BinOp(
            "/",
            Constant(23, TYPE_INTEGER),
            Constant(7, TYPE_INTEGER),
        ),
    )
