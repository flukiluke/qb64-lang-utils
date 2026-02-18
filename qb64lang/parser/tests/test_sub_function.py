from .. import diagnostics as diag
from .. import parse
from ..ast import (
    Assignment,
    Call,
    Cast,
    Constant,
    Print,
    ProcDeclaration,
    ProcDefinition,
    ProcDefinitionLocation,
    Procedure,
    SetReturn,
    Variable,
)
from ..datatypes import (
    TYPE__NONE,
    TYPE_DOUBLE,
    TYPE_INTEGER,
    TYPE_LONG,
    TYPE_SINGLE,
    TYPE_STRING,
    Parameter,
    TypeSignature,
)
from .helpers import Ast, parse_clean


def test_no_params():
    prog = parse_clean("""
        sub S
            print "hi"
        end sub
        function F
            print "bye"
        end function""")

    assert prog.symbols.find_procedure("s") == Procedure(
        "s",
        "S",
        [
            Ast(
                ProcDefinition,
                "s",
                TypeSignature(ret=TYPE__NONE, params=[]),
                statements=[Ast(Print)],
            )
        ],
    )
    assert prog.symbols.find_procedure("f") == Procedure(
        "f",
        "F",
        [
            Ast(
                ProcDefinition,
                "f",
                TypeSignature(ret=TYPE_SINGLE, params=[]),
                statements=[Ast(Print)],
            )
        ],
    )
    assert prog.main == Ast(
        ProcDefinition,
        "_main",
        TypeSignature(ret=TYPE__NONE, params=[]),
        statements=[Ast(ProcDefinitionLocation), Ast(ProcDefinitionLocation)],
    )


def test_mismatch_keyword_ok():
    parse_clean("sub s: end function : function f : end sub")


def test_sub_before_main():
    prog = parse_clean("""
        sub s
            print "hi"
            y = 2
        end sub
        x = 1""")
    proc = prog.symbols.find_procedure("s")
    assert proc is not None
    assert "y" in proc.impls[0].symbols.variables
    assert prog.main.find(Assignment) is not None
    assert "x" in prog.main.symbols.variables


def test_sub_after_main():
    prog = parse_clean("""
        x = 1
        sub s
            print "hi"
        end sub""")
    assert prog.symbols.find_procedure("s") is not None
    assert prog.main.find(Assignment) is not None
    assert "x" in prog.main.symbols.variables


def test_subs_main_interleaved():
    prog = parse_clean("""
        x = 1
        sub s
            print "hi"
        end sub
        x = 2
        function f: end function
        """)
    assert prog.symbols.find_procedure("s") is not None
    assert prog.symbols.find_procedure("f") is not None
    assert len(list(prog.main.find_all(Assignment))) == 2
    assert "x" in prog.main.symbols.variables


def test_function_return_type():
    prog = parse_clean("function f: end function")
    proc = prog.symbols.find_procedure("f")
    assert proc is not None
    assert proc.sigs()[0].ret == TYPE_SINGLE

    prog = parse_clean("function f&: end function")
    proc = prog.symbols.find_procedure("f")
    assert proc is not None
    assert proc.sigs()[0].ret == TYPE_LONG


def test_sub_return_type_disallowed():
    assert parse("sub s%: end sub").diagnostics.has(diag.E_SUB_WITH_TYPE)


def test_in_use_name():
    assert parse("sub if: end sub").diagnostics.has(diag.E_NAME_IN_USE)
    assert parse("sub s: end sub : sub s: end sub").diagnostics.has(diag.E_NAME_IN_USE)
    assert parse("function f: end function: sub f: end sub").diagnostics.has(
        diag.E_OVERLOAD_PROHIBITED
    )
    assert parse("x = 3: function x: end function").diagnostics.has(diag.E_NAME_IN_USE)
    assert parse("""
        sub s
            x = 3
        end sub
        function x: end function""").diagnostics.has(diag.E_NAME_IN_USE)


def test_proc_redefinition():
    assert parse(
        "function f!: end function: function f%: end function"
    ).diagnostics.has(diag.E_OVERLOAD_PROHIBITED)
    assert parse("function f: end function: function f%: end function").diagnostics.has(
        diag.E_OVERLOAD_PROHIBITED
    )
    assert parse("function f: end function: function f%: end function").diagnostics.has(
        diag.E_OVERLOAD_PROHIBITED
    )
    assert parse(
        "function f$: end function: function f%: end function"
    ).diagnostics.has(diag.E_OVERLOAD_PROHIBITED)
    assert parse(
        "function f(a) : end function : function f : end function"
    ).diagnostics.has(diag.E_OVERLOAD_PROHIBITED)
    assert parse(
        "function f(a$) : end function : function f(a) : end function"
    ).diagnostics.has(diag.E_OVERLOAD_PROHIBITED)


def test_one_param():
    prog = parse_clean("function f(A&) : end function")
    proc = prog.symbols.find_procedure("f")
    assert proc is not None
    assert proc.impls[0].signature == TypeSignature(
        TYPE_SINGLE, [Parameter(TYPE_LONG, "a", "A&")]
    )
    assert proc.impls[0].symbols.variables == {
        "a": {"long": Variable("a", "A&", TYPE_LONG)}
    }


def test_multi_param():
    prog = parse_clean("sub s(a&, b, c$) : end sub")
    proc = prog.symbols.find_procedure("s")
    assert proc is not None
    assert proc.impls[0].signature == TypeSignature(
        TYPE__NONE,
        [
            Parameter(TYPE_LONG, "a", "a&"),
            Parameter(TYPE_SINGLE, "b", "b"),
            Parameter(TYPE_STRING, "c", "c$"),
        ],
    )
    assert proc.impls[0].symbols.variables == {
        "a": {"long": Variable("a", "a&", TYPE_LONG)},
        "b": {"single": Variable("b", "b", TYPE_SINGLE)},
        "c": {"string": Variable("c", "c$", TYPE_STRING)},
    }


def test_param_as_clause():
    prog = parse_clean("sub s(a as long, b, c as string) : end sub")
    proc = prog.symbols.find_procedure("s")
    assert proc is not None
    assert proc.impls[0].signature == TypeSignature(
        TYPE__NONE,
        [
            Parameter(TYPE_LONG, "a", "a"),
            Parameter(TYPE_SINGLE, "b", "b"),
            Parameter(TYPE_STRING, "c", "c"),
        ],
    )


def test_local_var():
    prog = parse_clean("sub s: x = 3: end sub")
    proc = prog.symbols.find_procedure("s")
    assert proc is not None
    assert proc.impls[0].symbols.variables == {
        "x": {"single": Variable("x", "x", TYPE_SINGLE)}
    }


def test_param_name_in_use():
    assert parse("function f(if) : end function").diagnostics.has(diag.E_NAME_IN_USE)
    assert parse("function f(f) : end function").diagnostics.has(diag.E_NAME_IN_USE)


def test_function_recursion():
    prog = parse_clean("""
        function f(x)
            f = f(x - 1)
        end function""")
    proc = prog.symbols.find_procedure("f")
    assert proc is not None
    assert proc.impls[0].statements == [
        Ast(SetReturn, proc.impls[0], Ast(Call, proc, [Ast(Call)]))
    ]


def test_sub_recursion():
    prog = parse_clean("""
        sub s(x)
            s x - 1
        end sub""")
    proc = prog.symbols.find_procedure("s")
    assert proc is not None
    assert proc.impls[0].statements == [Ast(Call, proc, [Ast(Call)])]


def test_function_return():
    prog = parse_clean("""
        function f%(x%)
            f = x% + 1
            f% = x% + 2
            f% = 3.5
        end function""")
    proc = prog.symbols.find_procedure("f")
    assert proc is not None
    assert proc.impls[0].statements == [
        Ast(SetReturn, proc.impls[0], Ast(Call)),
        Ast(SetReturn, proc.impls[0], Ast(Call)),
        Ast(SetReturn, proc.impls[0], Cast(Ast(Constant), TYPE_INTEGER)),
    ]


def test_function_return_bad_type():
    assert parse("function f : f& = 3: end function").diagnostics.has(
        diag.E_EXISTING_DEF_SIGIL_CLASH
    )
    assert parse("function f! : f& = 3: end function").diagnostics.has(
        diag.E_EXISTING_DEF_SIGIL_CLASH
    )
    assert parse('function f! : f! = "hi": end function').diagnostics.has(
        diag.E_RETURN_MISMATCH
    )


def test_nested_proc():
    assert parse("sub s : sub t : end sub : end sub").diagnostics.has(
        diag.E_NESTED_PROC
    )


def test_declare_signatures():
    prog = parse_clean("declare sub Foo (a, b%): declare function bar#(c as string)")
    assert prog.main.statements == [
        Ast(
            ProcDeclaration,
            "foo",
            TypeSignature(
                TYPE__NONE,
                [Parameter(TYPE_SINGLE, "a", "a"), Parameter(TYPE_INTEGER, "b", "b%")],
            ),
        ),
        Ast(
            ProcDeclaration,
            "bar",
            TypeSignature(TYPE_DOUBLE, [Parameter(TYPE_STRING, "c", "c")]),
        ),
    ]
    assert prog.symbols.find_procedure("foo") == Procedure(
        "foo", "Foo", [Ast(ProcDefinition, "foo", decl_only=True)]
    )
    assert prog.symbols.find_procedure("bar") == Procedure(
        "bar", "bar#", [Ast(ProcDefinition, "bar", decl_only=True)]
    )


def test_declare_match_definition():
    prog = parse_clean("declare sub foo (a) : sub foo (a) : x = 1: end sub")
    assert prog.symbols.find_procedure("foo") == Procedure(
        "foo",
        "foo",
        [Ast(ProcDefinition, "foo", statements=[Ast(Assignment)], decl_only=False)],
    )


def test_declare_mismatch_definition():
    assert parse("declare sub foo (a) : sub foo (a%) : end sub").diagnostics.has(
        diag.E_OVERLOAD_PROHIBITED
    )


def test_multi_declare_mismatch():
    assert parse("declare sub foo (a) : declare sub foo (a%)").diagnostics.has(
        diag.E_OVERLOAD_PROHIBITED
    )


def test_repeated_declare():
    assert parse("declare sub foo (a) : declare sub foo (a)").diagnostics.has(
        diag.E_OVERLOAD_PROHIBITED
    )


def test_declare_overload():
    prog = parse_clean("$overload:on\ndeclare sub foo(a) : declare sub foo(a, b)")
    assert prog.symbols.find_procedure("foo") == Procedure(
        "foo",
        "foo",
        [
            Ast(
                ProcDefinition,
                "foo",
                decl_only=True,
                signature=TypeSignature(TYPE__NONE, [Parameter(TYPE_SINGLE, "a", "a")]),
            ),
            Ast(
                ProcDefinition,
                "foo",
                decl_only=True,
                signature=TypeSignature(
                    TYPE__NONE,
                    [
                        Parameter(TYPE_SINGLE, "a", "a"),
                        Parameter(TYPE_SINGLE, "b", "b"),
                    ],
                ),
            ),
        ],
    )


def test_declare_match_def_overload():
    prog = parse_clean(
        "$overload:on\ndeclare sub foo (a) : sub foo (a) : x = 1: end sub"
    )
    assert prog.symbols.find_procedure("foo") == Procedure(
        "foo",
        "foo",
        [Ast(ProcDefinition, "foo", statements=[Ast(Assignment)], decl_only=False)],
    )


def test_declare_mismatch_def_overload():
    prog = parse_clean("$overload:on\ndeclare sub foo (a) : sub foo (a%) : end sub")
    assert prog.symbols.find_procedure("foo") == Procedure(
        "foo",
        "foo",
        [
            Ast(
                ProcDefinition,
                "foo",
                decl_only=True,
                signature=TypeSignature(TYPE__NONE, [Parameter(TYPE_SINGLE, "a", "a")]),
            ),
            Ast(
                ProcDefinition,
                "foo",
                decl_only=False,
                signature=TypeSignature(
                    TYPE__NONE, [Parameter(TYPE_INTEGER, "a", "a%")]
                ),
            ),
        ],
    )


def test_def_overload():
    prog = parse_clean("$overload:on\n sub foo (a) : end sub : sub foo (a%) : end sub")
    assert prog.symbols.find_procedure("foo") == Procedure(
        "foo",
        "foo",
        [
            Ast(
                ProcDefinition,
                "foo",
                decl_only=False,
                signature=TypeSignature(TYPE__NONE, [Parameter(TYPE_SINGLE, "a", "a")]),
            ),
            Ast(
                ProcDefinition,
                "foo",
                decl_only=False,
                signature=TypeSignature(
                    TYPE__NONE, [Parameter(TYPE_INTEGER, "a", "a%")]
                ),
            ),
        ],
    )
