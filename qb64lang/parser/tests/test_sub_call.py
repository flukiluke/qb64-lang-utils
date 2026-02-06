from .. import diagnostics as diag
from .. import parse
from ..ast import Call, Cast, Constant
from ..datatypes import TYPE__NONE, TYPE_INTEGER, TYPE_SINGLE, TYPE_STRING
from .helpers import Ast, builtin_proc, parse_clean


def test_standard_sub_calls():
    assert parse_clean('mkdir "foo"').main.find(Call) == Ast(
        Call,
        builtin_proc("mkdir"),
        [Ast(Constant, "foo", TYPE_STRING)],
        impl=builtin_proc("mkdir").impls[0],
        expr_type=TYPE__NONE,
    )
    assert parse_clean("out 1, 2.2").main.find(Call) == Ast(
        Call,
        builtin_proc("out"),
        [Ast(Constant, 1, TYPE_INTEGER), Cast(Ast(Constant, 2.2), TYPE_INTEGER)],
        impl=builtin_proc("out").impls[0],
        expr_type=TYPE__NONE,
    )


def test_expr_argument():
    assert parse_clean("out 1 + 3, (2.2 + 1) * 2").main.find(Call) == Ast(
        Call, builtin_proc("out"), [Ast(Call), Cast(Ast(Call), TYPE_INTEGER)]
    )


def test_function_wrong_num_arguments():
    assert parse("out 1, 2, 3").diagnostics.has(diag.E_TOO_MANY_ARGUMENTS)
    assert parse("out").diagnostics.has(diag.E_NOT_ENOUGH_ARGUMENTS)


def test_function_wrong_type_arguments():
    assert parse("mkdir 3").diagnostics.has(diag.E_ARG_TYPE_MISMATCH)


def test_user_sub_call():
    prog = parse_clean("sub s(x): print x: end sub: s 3")
    assert prog.main.find(Call) == Ast(
        Call, prog.symbols.find_procedure("s"), [Cast(Ast(Constant, 3), TYPE_SINGLE)]
    )
