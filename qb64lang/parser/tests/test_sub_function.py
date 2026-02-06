from .. import diagnostics as diag
from .. import parse
from ..ast import (
    Assignment,
    Call,
    Cast,
    Constant,
    Print,
    ProcDefinitionLocation,
    Procedure,
    SetReturn,
    UserProcDefinition,
    Variable,
)
from ..datatypes import (
    TYPE__NONE,
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
        sub s
            print "hi"
        end sub
        function f
            print "bye"
        end function""")

    assert prog.symbols.find_procedure("s") == Procedure(
        "s",
        [
            Ast(
                UserProcDefinition,
                "s",
                TypeSignature(ret=TYPE__NONE, params=[]),
                statements=[Ast(Print)],
            )
        ],
    )
    assert prog.symbols.find_procedure("f") == Procedure(
        "f",
        [
            Ast(
                UserProcDefinition,
                "f",
                TypeSignature(ret=TYPE_SINGLE, params=[]),
                statements=[Ast(Print)],
            )
        ],
    )
    assert prog.main == Ast(
        UserProcDefinition,
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
    assert parse("function f: end function: sub f: end sub").diagnostics.has(
        diag.E_NAME_IN_USE
    )
    assert parse("x = 3: function x: end function").diagnostics.has(diag.E_NAME_IN_USE)
    assert parse("""
        sub s
            x = 3
        end sub
        function x: end function""").diagnostics.has(diag.E_NAME_IN_USE)


def test_sigil_clash():
    assert parse(
        "function f!: end function: function f%: end function"
    ).diagnostics.has(diag.E_EXISTING_DEF_SIGIL_CLASH)
    assert parse("function f: end function: function f%: end function").diagnostics.has(
        diag.E_EXISTING_DEF_SIGIL_CLASH
    )
    assert parse("function f: end function: function f%: end function").diagnostics.has(
        diag.E_EXISTING_DEF_SIGIL_CLASH
    )
    assert parse(
        "function f$: end function: function f%: end function"
    ).diagnostics.has(diag.E_EXISTING_DEF_SIGIL_CLASH)


def test_one_param():
    prog = parse_clean("function f(a&) : end function")
    proc = prog.symbols.find_procedure("f")
    assert proc is not None
    assert proc.impls[0].signature == TypeSignature(
        TYPE_SINGLE, [Parameter(TYPE_LONG, "a")]
    )
    assert proc.impls[0].symbols.variables == {"a": {"long": Variable("a", TYPE_LONG)}}


def test_multi_param():
    prog = parse_clean("sub s(a&, b, c$) : end sub")
    proc = prog.symbols.find_procedure("s")
    assert proc is not None
    assert proc.impls[0].signature == TypeSignature(
        TYPE__NONE,
        [
            Parameter(TYPE_LONG, "a"),
            Parameter(TYPE_SINGLE, "b"),
            Parameter(TYPE_STRING, "c"),
        ],
    )
    assert proc.impls[0].symbols.variables == {
        "a": {"long": Variable("a", TYPE_LONG)},
        "b": {"single": Variable("b", TYPE_SINGLE)},
        "c": {"string": Variable("c", TYPE_STRING)},
    }


def test_local_var():
    prog = parse_clean("sub s: x = 3: end sub")
    proc = prog.symbols.find_procedure("s")
    assert proc is not None
    assert proc.impls[0].symbols.variables == {
        "x": {"single": Variable("x", TYPE_SINGLE)}
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
    assert proc is not None and isinstance(proc.impls[0], UserProcDefinition)
    assert proc.impls[0].statements == [
        Ast(SetReturn, proc.impls[0], Ast(Call, proc, [Ast(Call)]))
    ]


def test_sub_recursion():
    prog = parse_clean("""
        sub s(x)
            s x - 1
        end sub""")
    proc = prog.symbols.find_procedure("s")
    assert proc is not None and isinstance(proc.impls[0], UserProcDefinition)
    assert proc.impls[0].statements == [Ast(Call, proc, [Ast(Call)])]


def test_function_return():
    prog = parse_clean("""
        function f%(x%)
            f = x% + 1
            f% = x% + 2
            f% = 3.5
        end function""")
    proc = prog.symbols.find_procedure("f")
    assert proc is not None and isinstance(proc.impls[0], UserProcDefinition)
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
