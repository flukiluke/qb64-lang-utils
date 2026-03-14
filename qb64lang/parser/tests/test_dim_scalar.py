from .. import diagnostics as diag
from .. import parse
from ..ast import Dim, DimScalarItem
from ..datatypes import TYPE__UNSIGNED_LONG, TYPE_LONG, TYPE_SINGLE, TYPE_STRING
from .helpers import Ast, parse_clean


def test_empty_list():
    assert parse("dim").diagnostics.has(diag.E_EMPTY_DIM)
    assert parse("dim as long").diagnostics.has(diag.E_EMPTY_DIM)


def test_bare_var():
    prog = parse_clean("dim x")
    var = prog.symbols.find_variable("x", TYPE_SINGLE)
    assert var is not None and var.type == TYPE_SINGLE
    assert prog.main.statements == [
        Ast(Dim, [Ast(DimScalarItem, var)], is_redim=False, leading_type=None)
    ]


def test_redim():
    prog = parse_clean("redim x")
    var = prog.symbols.find_variable("x", TYPE_SINGLE)
    assert var is not None and var.type == TYPE_SINGLE
    assert prog.main.statements == [
        Ast(Dim, [Ast(DimScalarItem, var)], is_redim=True, leading_type=None)
    ]


def test_leading_type():
    prog = parse_clean("dim as long x, y, z")
    var1 = prog.symbols.find_variable("x", TYPE_LONG)
    var2 = prog.symbols.find_variable("y", TYPE_LONG)
    var3 = prog.symbols.find_variable("z", TYPE_LONG)
    assert var1 is not None and var1.type == TYPE_LONG
    assert var2 is not None and var2.type == TYPE_LONG
    assert var3 is not None and var3.type == TYPE_LONG
    assert prog.main.statements == [
        Ast(
            Dim,
            [
                Ast(DimScalarItem, var1),
                Ast(DimScalarItem, var2),
                Ast(DimScalarItem, var3),
            ],
            is_redim=False,
            leading_type=TYPE_LONG,
        )
    ]


def test_trailing_type():
    prog = parse_clean("dim x as long, y, z as string")
    var1 = prog.symbols.find_variable("x", TYPE_LONG)
    var2 = prog.symbols.find_variable("y", TYPE_SINGLE)
    var3 = prog.symbols.find_variable("z", TYPE_STRING)
    assert var1 is not None and var1.type == TYPE_LONG
    assert var2 is not None and var2.type == TYPE_SINGLE
    assert var3 is not None and var3.type == TYPE_STRING
    assert prog.main.statements == [
        Ast(
            Dim,
            [
                Ast(DimScalarItem, var1),
                Ast(DimScalarItem, var2),
                Ast(DimScalarItem, var3),
            ],
            is_redim=False,
            leading_type=None,
        )
    ]


def test_sigils():
    prog = parse_clean("dim x&, y, z$")
    var1 = prog.symbols.find_variable("x", TYPE_LONG)
    var2 = prog.symbols.find_variable("y", TYPE_SINGLE)
    var3 = prog.symbols.find_variable("z", TYPE_STRING)
    assert var1 is not None and var1.type == TYPE_LONG
    assert var2 is not None and var2.type == TYPE_SINGLE
    assert var3 is not None and var3.type == TYPE_STRING
    assert prog.main.statements == [
        Ast(
            Dim,
            [
                Ast(DimScalarItem, var1),
                Ast(DimScalarItem, var2),
                Ast(DimScalarItem, var3),
            ],
            is_redim=False,
            leading_type=None,
        )
    ]


def test_multiple_types_clash():
    assert parse("dim as long x as long").diagnostics.has(diag.E_DUPE_AS_TYPE)
    assert parse("dim as long x&").diagnostics.has(diag.E_SIGIL_WITH_AS)
    assert parse("dim x& as long").diagnostics.has(diag.E_SIGIL_WITH_AS)
    assert parse("dim as single x as long").diagnostics.has(diag.E_DUPE_AS_TYPE)
    assert parse("dim as single x&").diagnostics.has(diag.E_SIGIL_WITH_AS)
    assert parse("dim x& as single").diagnostics.has(diag.E_SIGIL_WITH_AS)


def test_missing_comma():
    assert parse("dim x y").diagnostics.has(diag.E_UNEXPECTED_ITEM)
    assert parse("dim x as single y").diagnostics.has(diag.E_UNEXPECTED_ITEM)


def test_missing_type():
    assert parse("dim x as").diagnostics.has(diag.E_NOT_A_TYPE)


def test_as_unsigned():
    prog = parse_clean("dim as _unsigned long x")
    var = prog.symbols.find_variable("x", TYPE__UNSIGNED_LONG)
    assert var is not None and var.type == TYPE__UNSIGNED_LONG
    assert prog.main.statements == [
        Ast(
            Dim,
            [Ast(DimScalarItem, var)],
            is_redim=False,
            leading_type=TYPE__UNSIGNED_LONG,
        )
    ]


def test_bad_unsigned():
    assert parse("dim x as _unsigned").diagnostics.has(diag.E_NOT_A_TYPE)
    assert parse("dim x as _unsigned string").diagnostics.has(diag.E_NOT_A_TYPE)


def test_fixed_width_bit():
    prog = parse_clean("dim as _unsigned _bit * 7 x")
    type = prog.symbols.find_type("_unsigned _bit * 7")
    assert type is not None
    var = prog.symbols.find_variable("x", type)
    assert var is not None and var.type == type
    assert prog.main.statements == [
        Ast(Dim, [Ast(DimScalarItem, var)], is_redim=False, leading_type=type)
    ]


def test_fixed_width_string():
    prog = parse_clean("dim x as string * 100")
    type = prog.symbols.find_type("string * 100")
    assert type is not None
    var = prog.symbols.find_variable("x", type)
    assert var is not None and var.type == type
    assert prog.main.statements == [
        Ast(Dim, [Ast(DimScalarItem, var)], is_redim=False, leading_type=None)
    ]


def test_bad_fixed_width():
    assert parse("dim x as long * 3").diagnostics.has(diag.E_UNFIXABLE_TYPE)


def test_cannot_redim_scalar():
    assert parse("dim x : dim x").diagnostics.has(diag.E_DUPE_DIM)
    assert parse("dim x : redim x").diagnostics.has(diag.E_DUPE_DIM)
