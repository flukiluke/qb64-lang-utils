from qbparse import parse
from qbparse.ast import BuiltinProcDefinition, Call, Cast, Constant
from qbparse.datatypes import (
    TYPE__FLOAT,
    TYPE__INTEGER64,
    TYPE__UNSIGNED_INTEGER,
    TYPE_DOUBLE,
    TYPE_INTEGER,
    TYPE_LONG,
    TYPE_SINGLE,
    TYPE_STRING,
    ExtendedFloat,
    TypeSignature,
)

from .helpers import Ast


def check(input: str):
    result = parse(input)
    assert len(result.errors) == 0
    return result


def test_assignment():
    check("x = 3")
    check('x$ = "foo"')
    check("x = 3")
    assert len(parse("x$ = 3").errors) != 0


def test_operator_overload_int():
    """
    Exact argument match
    """
    expr = check("? 2% + 3%").main.find(Call)
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
    """
    Promotion of one argument
    """
    expr = check("? 2% - 3!").main.find(Call)
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


def test_operator_overload_mixed_unsigned():
    """
    Promotion of unsigned to larger signed
    """
    expr = check("? 2& * 3~%").main.find(Call)
    assert expr == Ast(
        Call,
        args=[
            Ast(Constant, 2, TYPE_LONG),
            Cast(Ast(Constant, 3, TYPE__UNSIGNED_INTEGER), TYPE_LONG),
        ],
        impl=Ast(
            BuiltinProcDefinition,
            TypeSignature(TYPE_LONG, [TYPE_LONG, TYPE_LONG]),
        ),
        expr_type=TYPE_LONG,
    )


def test_operator_overload_no_match():
    """
    Incompatible arguments
    """
    assert len(parse('? "foo" + 3').errors) > 0


def test_operator_overload_float_to_integral():
    """
    Rounding of float types to integral
    """
    expr = check("? not 3!").main.find(Call)
    assert expr == Ast(Call, args=[Cast(Ast(Constant, 3), TYPE__INTEGER64)])
    expr = check("? 4.1# and 5.5##").main.find(Call)
    assert expr == Ast(
        Call,
        args=[
            Cast(Ast(Constant, 4.1), TYPE__INTEGER64),
            Cast(Ast(Constant, ExtendedFloat("5.5")), TYPE__INTEGER64),
        ],
    )


def test_operator_overload_float_mixed_to_integral():
    """
    Rounding of float and integeral to integral
    """
    expr = check("? 3! and 4%").main.find(Call)
    assert expr == Ast(
        Call,
        args=[
            Cast(Ast(Constant, 3), TYPE__INTEGER64),
            Cast(Ast(Constant, 4), TYPE__INTEGER64),
        ],
    )


def test_operator_overload_integer_to_float():
    """
    Promotion of integers for float-only function
    """
    expr = check("? 2% / 3~`4").main.find(Call)
    assert expr == Ast(
        Call,
        args=[
            Cast(Ast(Constant, 2), TYPE_SINGLE),
            Cast(Ast(Constant, 3), TYPE_SINGLE),
        ],
        impl=Ast(
            BuiltinProcDefinition,
            TypeSignature(TYPE_SINGLE, [TYPE_SINGLE, TYPE_SINGLE]),
        ),
        expr_type=TYPE_SINGLE,
    )


def test_operator_overload_long_to_float():
    """
    Promotion of long for float-only function
    """
    expr = check("? 2& / 3%").main.find(Call)
    assert expr == Ast(
        Call,
        args=[
            Cast(Ast(Constant, 2), TYPE_DOUBLE),
            Cast(Ast(Constant, 3), TYPE_DOUBLE),
        ],
        impl=Ast(
            BuiltinProcDefinition,
            TypeSignature(TYPE_DOUBLE, [TYPE_DOUBLE, TYPE_DOUBLE]),
        ),
        expr_type=TYPE_DOUBLE,
    )


def test_operator_overload_in64_to_float():
    """
    Promotion of _integer64 for float-only function
    """
    expr = check("? 2&& / 3~&&").main.find(Call)
    assert expr == Ast(
        Call,
        args=[
            Cast(Ast(Constant, 2), TYPE__FLOAT),
            Cast(Ast(Constant, 3), TYPE__FLOAT),
        ],
        impl=Ast(
            BuiltinProcDefinition,
            TypeSignature(TYPE__FLOAT, [TYPE__FLOAT, TYPE__FLOAT]),
        ),
        expr_type=TYPE__FLOAT,
    )


def test_operator_overload_mixed_to_float():
    """
    Promotion of integral and float types for float-only function
    """
    expr = check("? 2& / 3!").main.find(Call)
    assert expr == Ast(
        Call,
        args=[
            Cast(Ast(Constant, 2), TYPE_DOUBLE),
            Cast(Ast(Constant, 3), TYPE_DOUBLE),
        ],
        impl=Ast(
            BuiltinProcDefinition,
            TypeSignature(TYPE_DOUBLE, [TYPE_DOUBLE, TYPE_DOUBLE]),
        ),
        expr_type=TYPE_DOUBLE,
    )


def test_standard_function_calls():
    expr = check('? lcase$("foo")').main.find(Call)
    assert expr == Ast(Call, args=[Ast(Constant, "foo")], expr_type=TYPE_STRING)
    expr = check("? _atan2(3, 4)").main.find(Call)
    assert expr == Ast(
        Call,
        args=[Cast(Ast(Constant, 3), TYPE_SINGLE), Cast(Ast(Constant, 4), TYPE_SINGLE)],
        expr_type=TYPE_SINGLE,
    )


def test_function_wrong_num_arguments():
    assert len(parse('? lcase$("foo","bar")').errors) > 0
    assert len(parse("? _atan2(3)").errors) > 0


def test_function_wrong_type_arguments():
    assert len(parse("? lcase$(3)").errors) > 0
    assert len(parse('? _atan2("foo")').errors) > 0
