from qb64lang.parser.datatypes import Parameter as P

from .. import diagnostics as diag
from .. import parse
from ..ast import BuiltinProcDefinition, Call, Cast, Constant
from ..datatypes import (
    TYPE__BYTE,
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
from .helpers import Ast, builtin_proc, parse_clean


def test_assignment():
    parse_clean("x = 3")
    parse_clean('x$ = "foo"')
    parse_clean("x = 3")
    assert parse("x$ = 3").diagnostics.has(diag.E_ASSIGNMENT_MISMATCH)


def test_equality():
    expr = parse_clean("? 1% = 2%").main.find(Call)
    assert expr == Ast(
        Call,
        builtin_proc("="),
        args=[Ast(Constant, 1), Ast(Constant, 2)],
        expr_type=TYPE__BYTE,
    )
    expr = parse_clean("? 1% = 2&").main.find(Call)
    assert expr == Ast(
        Call,
        args=[Cast(Ast(Constant, 1), TYPE_LONG), Ast(Constant, 2)],
    )
    expr = parse_clean("? 1& = 2%").main.find(Call)
    assert expr == Ast(
        Call,
        args=[Ast(Constant, 1), Cast(Ast(Constant, 2), TYPE_LONG)],
    )
    expr = parse_clean("? 1! = 2%").main.find(Call)
    assert expr == Ast(
        Call,
        args=[Ast(Constant, 1), Cast(Ast(Constant, 2), TYPE_SINGLE)],
    )
    expr = parse_clean("? 1! = 2#").main.find(Call)
    assert expr == Ast(
        Call,
        args=[
            Cast(Ast(Constant, 1), TYPE_DOUBLE),
            Ast(Constant, 2),
        ],
    )
    expr = parse_clean("? 1&& = 2#").main.find(Call)
    assert expr == Ast(
        Call,
        args=[Cast(Ast(Constant, 1), TYPE__FLOAT), Cast(Ast(Constant, 2), TYPE__FLOAT)],
    )
    expr = parse_clean('? "foo" = "bar"').main.find(Call)
    assert expr == Ast(
        Call,
        args=[
            Ast(Constant, "foo"),
            Ast(Constant, "bar"),
        ],
    )


def test_equality_errors():
    assert parse('? "foo" = 2').diagnostics.has(diag.E_NO_MATCHING_OVERLOAD)
    assert parse('? 2 = "foo"').diagnostics.has(diag.E_NO_MATCHING_OVERLOAD)


def test_operator_overload_int():
    """
    Exact argument match
    """
    expr = parse_clean("? 2% + 3%").main.find(Call)
    assert expr == Ast(
        Call,
        args=[
            Ast(Constant, 2, TYPE_INTEGER),
            Ast(Constant, 3, TYPE_INTEGER),
        ],
        impl=Ast(
            BuiltinProcDefinition,
            TypeSignature(TYPE_INTEGER, [P(TYPE_INTEGER), P(TYPE_INTEGER)]),
        ),
        expr_type=TYPE_INTEGER,
    )


def test_operator_overload_mixed_num():
    """
    Promotion of one argument
    """
    expr = parse_clean("? 2% - 3!").main.find(Call)
    assert expr == Ast(
        Call,
        args=[
            Cast(Ast(Constant, 2, TYPE_INTEGER), TYPE_SINGLE),
            Ast(Constant, 3, TYPE_SINGLE),
        ],
        impl=Ast(
            BuiltinProcDefinition,
            TypeSignature(TYPE_SINGLE, [P(TYPE_SINGLE), P(TYPE_SINGLE)]),
        ),
        expr_type=TYPE_SINGLE,
    )


def test_operator_overload_mixed_unsigned():
    """
    Promotion of unsigned to larger signed
    """
    expr = parse_clean("? 2& * 3~%").main.find(Call)
    assert expr == Ast(
        Call,
        args=[
            Ast(Constant, 2, TYPE_LONG),
            Cast(Ast(Constant, 3, TYPE__UNSIGNED_INTEGER), TYPE_LONG),
        ],
        impl=Ast(
            BuiltinProcDefinition,
            TypeSignature(TYPE_LONG, [P(TYPE_LONG), P(TYPE_LONG)]),
        ),
        expr_type=TYPE_LONG,
    )


def test_operator_overload_no_match():
    """
    Incompatible arguments
    """
    assert parse('? "foo" + 3').diagnostics.has(diag.E_NO_MATCHING_OVERLOAD)


def test_operator_overload_float_to_integral():
    """
    Rounding of float types to integral
    """
    expr = parse_clean("? not 3!").main.find(Call)
    assert expr == Ast(Call, args=[Cast(Ast(Constant, 3), TYPE__INTEGER64)])
    expr = parse_clean("? 4.1# and 5.5##").main.find(Call)
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
    expr = parse_clean("? 3! and 4%").main.find(Call)
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
    expr = parse_clean("? 2% / 3~`4").main.find(Call)
    assert expr == Ast(
        Call,
        args=[
            Cast(Ast(Constant, 2), TYPE_SINGLE),
            Cast(Ast(Constant, 3), TYPE_SINGLE),
        ],
        impl=Ast(
            BuiltinProcDefinition,
            TypeSignature(TYPE_SINGLE, [P(TYPE_SINGLE), P(TYPE_SINGLE)]),
        ),
        expr_type=TYPE_SINGLE,
    )


def test_operator_overload_long_to_float():
    """
    Promotion of long for float-only function
    """
    expr = parse_clean("? 2& / 3%").main.find(Call)
    assert expr == Ast(
        Call,
        args=[
            Cast(Ast(Constant, 2), TYPE_DOUBLE),
            Cast(Ast(Constant, 3), TYPE_DOUBLE),
        ],
        impl=Ast(
            BuiltinProcDefinition,
            TypeSignature(TYPE_DOUBLE, [P(TYPE_DOUBLE), P(TYPE_DOUBLE)]),
        ),
        expr_type=TYPE_DOUBLE,
    )


def test_operator_overload_in64_to_float():
    """
    Promotion of _integer64 for float-only function
    """
    expr = parse_clean("? 2&& / 3~&&").main.find(Call)
    assert expr == Ast(
        Call,
        args=[
            Cast(Ast(Constant, 2), TYPE__FLOAT),
            Cast(Ast(Constant, 3), TYPE__FLOAT),
        ],
        impl=Ast(
            BuiltinProcDefinition,
            TypeSignature(TYPE__FLOAT, [P(TYPE__FLOAT), P(TYPE__FLOAT)]),
        ),
        expr_type=TYPE__FLOAT,
    )


def test_operator_overload_mixed_to_float():
    """
    Promotion of integral and float types for float-only function
    """
    expr = parse_clean("? 2& / 3!").main.find(Call)
    assert expr == Ast(
        Call,
        args=[
            Cast(Ast(Constant, 2), TYPE_DOUBLE),
            Cast(Ast(Constant, 3), TYPE_DOUBLE),
        ],
        impl=Ast(
            BuiltinProcDefinition,
            TypeSignature(TYPE_DOUBLE, [P(TYPE_DOUBLE), P(TYPE_DOUBLE)]),
        ),
        expr_type=TYPE_DOUBLE,
    )


def test_standard_function_calls():
    expr = parse_clean('? lcase$("foo")').main.find(Call)
    assert expr == Ast(Call, args=[Ast(Constant, "foo")], expr_type=TYPE_STRING)
    expr = parse_clean("? _atan2(3, 4)").main.find(Call)
    assert expr == Ast(
        Call,
        args=[Cast(Ast(Constant, 3), TYPE_SINGLE), Cast(Ast(Constant, 4), TYPE_SINGLE)],
        expr_type=TYPE_SINGLE,
    )


def test_function_wrong_num_arguments():
    assert parse('? lcase$("foo","bar")').diagnostics.has(diag.E_TOO_MANY_ARGUMENTS)
    assert parse("? lcase$").diagnostics.has(diag.E_NOT_ENOUGH_ARGUMENTS)
    assert parse("? _atan2(3)").diagnostics.has(diag.E_NO_MATCHING_OVERLOAD)


def test_function_wrong_type_arguments():
    assert parse("? lcase$(3)").diagnostics.has(diag.E_ARG_TYPE_MISMATCH)
    assert parse('? _atan2("foo")').diagnostics.has(diag.E_NO_MATCHING_OVERLOAD)
