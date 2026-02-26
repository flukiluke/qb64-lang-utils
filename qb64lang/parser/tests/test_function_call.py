from .. import diagnostics as diag
from .. import parse
from ..ast import Call, Cast, Constant
from ..datatypes import TYPE_SINGLE, TYPE_STRING
from .helpers import Ast, parse_clean


def test_standard_function_calls():
    expr = parse_clean('? lcase$("foo")').main.find(Call)
    assert expr == Ast(Call, args=[Ast(Constant, "foo")], expr_type=TYPE_STRING)
    expr = parse_clean("? _atan2(3, 4)").main.find(Call)
    assert expr == Ast(
        Call,
        args=[
            Ast(Cast, Ast(Constant, 3), TYPE_SINGLE),
            Ast(Cast, Ast(Constant, 4), TYPE_SINGLE),
        ],
        expr_type=TYPE_SINGLE,
    )


def test_function_wrong_num_arguments():
    assert parse('? lcase$("foo","bar")').diagnostics.has(diag.E_TOO_MANY_ARGUMENTS)
    assert parse("? lcase$").diagnostics.has(diag.E_NOT_ENOUGH_ARGUMENTS)
    assert parse("? _atan2(3)").diagnostics.has(diag.E_NO_MATCHING_OVERLOAD)


def test_function_wrong_type_arguments():
    assert parse("? lcase$(3)").diagnostics.has(diag.E_ARG_TYPE_MISMATCH)
    assert parse('? _atan2("foo")').diagnostics.has(diag.E_NO_MATCHING_OVERLOAD)


def test_function_sigil_elision():
    prog = parse_clean("function f%: end function: ? f")
    assert prog.main.find(Call) == Ast(Call, prog.symbols.find_procedure("f"))


def test_function_sigil_misuse():
    assert parse("function f% : end function : ? f&").diagnostics.has(
        diag.E_EXISTING_DEF_SIGIL_CLASH
    )


def test_user_function_call():
    prog = parse_clean("function f(x): print x: end function: a = f(3.0)")
    assert prog.main.find(Call) == Ast(
        Call,
        prog.symbols.find_procedure("f"),
        [Ast(Constant, 3, TYPE_SINGLE)],
        expr_type=TYPE_SINGLE,
    )
