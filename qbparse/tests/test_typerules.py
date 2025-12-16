from qbparse import parse
from qbparse.ast import BuiltinProcDefinition, Call, Cast, Constant
from qbparse.datatypes import TYPE_INTEGER, TYPE_SINGLE, TypeSignature

from .helpers import Ast


def okay(input: str):
    return len(parse(input).errors) == 0


def test_assignment():
    assert okay("x = 3")
    assert okay('x$ = "foo"')
    assert not okay("x$ = 3")
    assert okay("x = 3")


def test_operator_overload_int():
    expr = parse("? 2% + 3%").main.find(Call)
    assert expr == Ast(
        Call,
        args=[
            Ast(Constant, 2, TYPE_INTEGER),
            Ast(Constant, 3, TYPE_INTEGER),
        ],
        impl=Ast(
            BuiltinProcDefinition,
            TypeSignature(TYPE_INTEGER, [TYPE_INTEGER, TYPE_INTEGER]),
        ),
        expr_type=TYPE_INTEGER,
    )


def test_operator_overload_mixed_num():
    expr = parse("? 2% + 3!").main.find(Call)
    assert expr == Ast(
        Call,
        args=[
            Cast(Ast(Constant, 2, TYPE_INTEGER), TYPE_SINGLE),
            Ast(Constant, 3, TYPE_SINGLE),
        ],
        impl=Ast(
            BuiltinProcDefinition,
            TypeSignature(TYPE_SINGLE, [TYPE_SINGLE, TYPE_SINGLE]),
        ),
        expr_type=TYPE_SINGLE,
    )
