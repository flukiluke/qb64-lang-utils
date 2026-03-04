from .. import diagnostics as diag
from .. import parse
from ..ast import CompoundDefinition, CompoundFieldDefinition
from ..datatypes import TYPE_LONG, TYPE_STRING, CompoundField, CompoundType
from .helpers import Ast, parse_clean


def test_definition_node():
    prog = parse_clean(
        """type t
            a as long
            as string b, c
        end type"""
    )
    assert prog.main.find(CompoundDefinition) == Ast(
        CompoundDefinition,
        prog.symbols.find_type("t"),
        [
            Ast(CompoundFieldDefinition, [CompoundField(TYPE_LONG, "a", "a")]),
            Ast(
                CompoundFieldDefinition,
                [
                    CompoundField(TYPE_STRING, "b", "b"),
                    CompoundField(TYPE_STRING, "c", "c"),
                ],
            ),
        ],
    )


def test_var_as_type():
    type = parse_clean(
        """type Foo
            Bar as long
            Baz as string
        end type"""
    ).symbols.find_type("foo")
    assert type is not None
    assert type == CompoundType(
        "foo",
        "Foo",
        "",
        [
            CompoundField(TYPE_LONG, "bar", "Bar"),
            CompoundField(TYPE_STRING, "baz", "Baz"),
        ],
    )


def test_as_type_var():
    type = parse_clean(
        """type Foo
            as long Bar
            as string Baz,Qux
        end type"""
    ).symbols.find_type("foo")
    assert type is not None
    assert type == CompoundType(
        "foo",
        "Foo",
        "",
        [
            CompoundField(TYPE_LONG, "bar", "Bar"),
            CompoundField(TYPE_STRING, "baz", "Baz"),
            CompoundField(TYPE_STRING, "qux", "Qux"),
        ],
    )


def test_empty_compound():
    assert parse("type foo : end type").diagnostics.has(diag.E_EMPTY_COMPOUND)


def test_dupe_field():
    prog = parse("type foo : a as long : a as single: end type")
    assert prog.diagnostics.has(diag.E_DUPE_COMPOUND_FIELD)
    assert prog.symbols.find_type("foo") == CompoundType(
        "foo", "foo", "", [CompoundField(TYPE_LONG, "a", "a")]
    )


def test_names_like_keyword():
    assert parse("type print : a as long: end type").diagnostics.has(diag.E_NAME_IN_USE)
    assert parse("type foo : print as long: end type").diagnostics.has(
        diag.E_NAME_IN_USE
    )
    assert parse("type integer : a as long: end type").diagnostics.has(
        diag.E_NAME_IN_USE
    )
    assert parse("type foo : integer as long: end type").diagnostics.has(
        diag.E_NAME_IN_USE
    )


def test_names_like_proc():
    parse_clean("type val : a as long : end type")
    parse_clean("type foo : val as long : end type")


def test_direct_recursion_illegal():
    assert parse("type t : a as t : end type").diagnostics.has(diag.E_NOT_A_TYPE)


def test_forward_type_reference_illegal():
    assert parse(
        """type t1
            a as t2
           end type
           type t2
            a as long
           end type"""
    ).diagnostics.has(diag.E_NOT_A_TYPE)
