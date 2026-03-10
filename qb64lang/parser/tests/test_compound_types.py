from .. import diagnostics as diag
from .. import parse
from ..ast import Assignment, CompoundDefinition, FieldAccess, Print, Var
from ..datatypes import TYPE_LONG, TYPE_SINGLE, TYPE_STRING, CompoundField, CompoundType
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


def test_dot_prohibited():
    assert parse("type a.b: x as long: end type").diagnostics.has(diag.E_DOT_PROHIBITED)
    assert parse("type a: x.b as long: end type").diagnostics.has(diag.E_DOT_PROHIBITED)
    assert parse("type a: as long x.b: end type").diagnostics.has(diag.E_DOT_PROHIBITED)


def test_field_access():
    prog = parse_clean("type t: a as long: end type: dim x as t: print x.a")
    type = prog.symbols.find_type("t")
    assert type is not None
    var = prog.symbols.find_variable("x", type=type)
    assert var and var.type == type and isinstance(type, CompoundType)
    assert prog.main.find(Print) == Ast(
        Print, [Ast(FieldAccess, Ast(Var, var), type.fields[0])]
    )


def test_nested_field_access():
    prog = parse_clean("""
        type s
            a as long
            b as string
        end type
        type t
            c as single
            d as s
        end type
        dim x as t
        print x.d.a
    """)
    type_s = prog.symbols.find_type("s")
    type_t = prog.symbols.find_type("t")
    assert type_t is not None
    var = prog.symbols.find_variable("x", type=type_t)
    assert isinstance(type_s, CompoundType)
    assert isinstance(type_t, CompoundType)
    assert var and var.type == type_t
    assert prog.main.find(Print) == Ast(
        Print,
        [
            Ast(
                FieldAccess,
                Ast(FieldAccess, Ast(Var, var), type_t.fields[1]),
                type_s.fields[0],
            )
        ],
    )


def test_field_on_non_compound():
    assert parse("""
        type t
            a as long
        end type
        dim x as t
        print x.a.b
    """).diagnostics.has(diag.E_FIELD_ACCESS_NON_COMPOUND)


def test_non_existent_field():
    assert parse("""
        type t
            a as long
        end type
        dim x as t
        print x.b
    """).diagnostics.has(diag.E_UNKNOWN_FIELD)


def test_dotted_non_compound():
    prog = parse_clean("x = a.b : print a.b")
    var = prog.symbols.find_variable("a.b", None)
    assert var is not None
    assert var.type == TYPE_SINGLE
    a1 = prog.main.find(Assignment).rval
    a2 = prog.main.find(Print).args[0]
    assert isinstance(a1, Var) and isinstance(a2, Var)
    assert a1.target == var
    assert a2.target == var
