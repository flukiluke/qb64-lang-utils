from .. import diagnostics as diag
from .. import parse
from ..ast import Call, Cast, Constant
from ..datatypes import TYPE__NONE, TYPE_INTEGER, TYPE_SINGLE, TYPE_STRING
from .helpers import Ast, parse_clean


def test_standard_sub_calls():
    prog = parse_clean('mkdir "foo"')
    proc = prog.symbols.find_procedure("mkdir")
    assert proc is not None
    assert prog.main.find(Call) == Ast(
        Call,
        proc,
        [Ast(Constant, "foo", TYPE_STRING)],
        impl=proc.impls[0],
        expr_type=TYPE__NONE,
    )

    prog = parse_clean("out 1, 2.2")
    proc = prog.symbols.find_procedure("out")
    assert proc is not None
    assert prog.main.find(Call) == Ast(
        Call,
        proc,
        [Ast(Constant, 1, TYPE_INTEGER), Ast(Cast, Ast(Constant, 2.2), TYPE_INTEGER)],
        impl=proc.impls[0],
        expr_type=TYPE__NONE,
    )


def test_expr_argument():
    prog = parse_clean("out 1 + 3, (2.2 + 1) * 2")
    proc = prog.symbols.find_procedure("out")
    assert proc is not None
    assert prog.main.find(Call) == Ast(
        Call, proc, [Ast(Call), Ast(Cast, Ast(Call), TYPE_INTEGER)]
    )


def test_function_wrong_num_arguments():
    assert parse("out 1, 2, 3").diagnostics.has(diag.E_TOO_MANY_ARGUMENTS)
    assert parse("out").diagnostics.has(diag.E_NOT_ENOUGH_ARGUMENTS)


def test_function_wrong_type_arguments():
    assert parse("mkdir 3").diagnostics.has(diag.E_ARG_TYPE_MISMATCH)


def test_user_sub_call():
    prog = parse_clean("sub s(x): print x: end sub: s 3")
    assert prog.main.find(Call) == Ast(
        Call,
        prog.symbols.find_procedure("s"),
        [Ast(Cast, Ast(Constant, 3), TYPE_SINGLE)],
    )
