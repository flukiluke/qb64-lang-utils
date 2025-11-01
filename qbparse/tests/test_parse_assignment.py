from qbparse import parse
from qbparse.ast import Assignment, BinOp, Constant, Var
from qbparse.datatypes import BUILTIN_TYPES


def run(input: str, variable_name: str):
    program = parse(input)
    impl = program.globals.procedures["_main"].impl
    assert impl is not None
    variable = program.globals.find_variable(variable_name)
    assert variable is not None
    assert variable.name == variable_name
    return (impl, variable)


def test_implicit_scalar():
    impl, variable = run("x = 5", "x")
    assert impl.find(Assignment) == Assignment(
        Var(variable), Constant(5, BUILTIN_TYPES["single"])
    )


def test_existing_scalar():
    impl, variable = run("foo = 32 : foo = 17", "foo")
    assert list(impl.find_all(Assignment)) == [
        Assignment(Var(variable), Constant(32, BUILTIN_TYPES["single"])),
        Assignment(Var(variable), Constant(17, BUILTIN_TYPES["single"])),
    ]


def test_expression_rvalue():
    impl, variable = run("foo = 23 / 7", "foo")
    assert impl.find(Assignment) == Assignment(
        Var(variable),
        BinOp(
            "/",
            Constant(23, BUILTIN_TYPES["single"]),
            Constant(7, BUILTIN_TYPES["single"]),
        ),
    )
