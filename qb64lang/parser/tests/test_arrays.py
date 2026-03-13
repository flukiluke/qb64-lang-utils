from .. import diagnostics as diag
from .. import parse
from ..ast import (
    ArrayAccess,
    Assignment,
    Call,
    Cast,
    Constant,
    Dim,
    DimArrayItem,
    DimScalarItem,
    Print,
    Var,
)
from ..datatypes import TYPE__INTEGER64, TYPE_SINGLE, TYPE_STRING, ArrayType
from .helpers import Ast, builtin_proc, parse_clean


def test_dim_one_dimension():
    prog = parse_clean("dim x(3)")
    type = prog.symbols.find_type("single[1]")
    var = prog.symbols.find_variable("x", None, as_array=True)
    assert type is not None and isinstance(type, ArrayType)
    assert not type.is_builtin()
    assert type.element_type == TYPE_SINGLE
    assert type.dimensions == 1
    assert prog.main.find(Dim) == Ast(
        Dim, [Ast(DimArrayItem, var, [Ast(Cast, Ast(Constant, 3))])]
    )


def test_dim_multi_dimensions():
    prog = parse_clean("dim x(3, 8)")
    type = prog.symbols.find_type("single[2]")
    var = prog.symbols.find_variable("x", None, as_array=True)
    assert var is not None
    assert type is not None and isinstance(type, ArrayType)
    assert type.dimensions == 2
    assert prog.main.find(Dim) == Ast(
        Dim,
        [
            Ast(
                DimArrayItem,
                var,
                [Ast(Cast, Ast(Constant, 3)), Ast(Cast, Ast(Constant, 8))],
            )
        ],
    )


def test_redim():
    prog = parse_clean("dim x(1, 2) : redim x(3, 4)")
    type = prog.symbols.find_type("single[2]")
    var = prog.symbols.find_variable("x", None, as_array=True)
    assert var is not None
    assert type is not None and isinstance(type, ArrayType)
    assert type.dimensions == 2
    assert prog.main.find_all(Dim) == [
        Ast(Dim, is_redim=False),
        Ast(Dim, [Ast(DimArrayItem, var)], is_redim=True),
    ]


def test_custom_lbound():
    prog = parse_clean("dim x(1 to 3, -5 to 8)")
    type = prog.symbols.find_type("single[2]")
    var = prog.symbols.find_variable("x", None, as_array=True)
    assert var is not None
    assert type is not None and isinstance(type, ArrayType)
    assert type.dimensions == 2
    assert prog.main.find(Dim) == Ast(
        Dim,
        [
            Ast(
                DimArrayItem,
                var,
                [
                    (Ast(Cast, Ast(Constant, 1)), Ast(Cast, Ast(Constant, 3))),
                    (
                        Ast(Cast, Ast(Call, builtin_proc("-"), [Ast(Constant, 5)])),
                        Ast(Cast, Ast(Constant, 8)),
                    ),
                ],
            )
        ],
    )


def test_dim_sigil():
    prog = parse_clean("dim x$(3)")
    type = prog.symbols.find_type("string[1]")
    var = prog.symbols.find_variable("x", type)
    assert var is not None
    assert type is not None and isinstance(type, ArrayType)
    assert not type.is_builtin()
    assert type.element_type == TYPE_STRING
    assert type.dimensions == 1
    assert prog.main.find(Dim) == Ast(
        Dim, [Ast(DimArrayItem, var, [Ast(Cast, Ast(Constant, 3))])]
    )


def test_dim_as_post():
    prog = parse_clean("dim x(3) as string")
    type = prog.symbols.find_type("string[1]")
    var = prog.symbols.find_variable("x", type)
    assert prog.main.find(Dim) == Ast(
        Dim, [Ast(DimArrayItem, var, [Ast(Cast, Ast(Constant, 3))])]
    )


def test_dim_as_pre():
    prog = parse_clean("dim as string x(3), y(4, 5)")
    type1 = prog.symbols.find_type("string[1]")
    type2 = prog.symbols.find_type("string[2]")
    var1 = prog.symbols.find_variable("x", type1)
    var2 = prog.symbols.find_variable("y", type2)
    assert prog.main.find(Dim) == Ast(
        Dim,
        [
            Ast(DimArrayItem, var1, [Ast(Cast, Ast(Constant, 3))]),
            Ast(
                DimArrayItem,
                var2,
                [Ast(Cast, Ast(Constant, 4)), Ast(Cast, Ast(Constant, 5))],
            ),
        ],
    )


def test_dim_mixed_scalar_array():
    prog = parse_clean("dim as string x(3), y")
    type1 = prog.symbols.find_type("string[1]")
    var1 = prog.symbols.find_variable("x", type1)
    var2 = prog.symbols.find_variable("y", TYPE_STRING)
    assert prog.main.find(Dim) == Ast(
        Dim,
        [
            Ast(DimArrayItem, var1, [Ast(Cast, Ast(Constant, 3))]),
            Ast(DimScalarItem, var2),
        ],
    )


def test_uni_index():
    prog = parse_clean("dim x(2) : print x(0)")
    type = prog.symbols.find_type("single[1]")
    var = prog.symbols.find_variable("x", type)
    assert prog.main.find(Print) == Ast(
        Print,
        [
            Ast(
                ArrayAccess,
                Ast(Var, var),
                [Ast(Cast, Ast(Constant, 0), TYPE__INTEGER64)],
            )
        ],
    )


def test_multi_index():
    prog = parse_clean("dim x(2, 3, 4) : print x(0, 1, 2)")
    type = prog.symbols.find_type("single[3]")
    var = prog.symbols.find_variable("x", type)
    assert prog.main.find(Print) == Ast(
        Print,
        [
            Ast(
                ArrayAccess,
                Ast(Var, var),
                [
                    Ast(Cast, Ast(Constant, 0), TYPE__INTEGER64),
                    Ast(Cast, Ast(Constant, 1), TYPE__INTEGER64),
                    Ast(Cast, Ast(Constant, 2), TYPE__INTEGER64),
                ],
            )
        ],
    )


def test_non_numeric_dim():
    assert parse('dim x("foo")').diagnostics.has(diag.E_NON_NUMERIC_EXPR)
    assert parse('dim x("foo" to 3)').diagnostics.has(diag.E_NON_NUMERIC_EXPR)
    assert parse('dim x(1 to "foo")').diagnostics.has(diag.E_NON_NUMERIC_EXPR)


def test_non_numeric_index():
    assert parse('dim x(3) : print x("foo")').diagnostics.has(diag.E_NON_NUMERIC_EXPR)


def test_bad_dimension():
    assert parse("dim x(3,2) : print x(1)").diagnostics.has(diag.E_ARRAY_BAD_NUM_DIMS)
    assert parse("dim x(3) : print x(1,2)").diagnostics.has(diag.E_ARRAY_BAD_NUM_DIMS)


def test_array_scalar_name_clashes():
    prog = parse_clean("dim x(2), x : print x; x(1)")
    scalar_var = prog.symbols.find_variable("x", TYPE_SINGLE)
    array_var = prog.symbols.find_variable("x", TYPE_SINGLE, as_array=True)
    assert prog.main.find(Print) == Ast(
        Print,
        [
            Ast(Var, scalar_var),
            Print.Element.SEMICOLON,
            Ast(ArrayAccess, Ast(Var, array_var), [Ast(Cast, Ast(Constant, 1))]),
        ],
    )


def test_cannot_change_dimensions():
    parse_clean("dim x(1,2) : dim x(1)")


def test_implicit_array():
    prog = parse_clean("x(2) = x(3)")
    var = prog.symbols.find_variable("x", TYPE_SINGLE, True)
    assert var is not None
    assert var.type == prog.symbols.find_type("single[1]")
    assert prog.main.find(Assignment).lval == Ast(
        ArrayAccess, Ast(Var, var), [Ast(Cast, Ast(Constant, 2))]
    )
    assert prog.main.find(Assignment).rval == Ast(
        ArrayAccess, Ast(Var, var), [Ast(Cast, Ast(Constant, 3))]
    )


def test_implicit_nested_array():
    prog = parse_clean("x(x(1, 2), 3) = 4")
    var = prog.symbols.find_variable("x", TYPE_SINGLE, True)
    assert var is not None
    assert var.type == prog.symbols.find_type("single[2]")
    assert prog.main.find(Assignment).lval == Ast(
        ArrayAccess,
        Ast(Var, var),
        [
            Ast(
                Cast,
                Ast(
                    ArrayAccess,
                    Ast(Var, var),
                    [
                        Ast(Cast, Ast(Constant, 1)),
                        Ast(Cast, Ast(Constant, 2)),
                    ],
                ),
            ),
            Ast(Cast, Ast(Constant, 3)),
        ],
    )


def test_implicit_nested_bad_dims():
    assert parse("x(1, x(2)) = 3").diagnostics.has(diag.E_ARRAY_BAD_NUM_DIMS)
