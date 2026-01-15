import qbparse.diagnostics as diag
from qbparse import parse
from qbparse.ast import Assignment, Print, ProcDefinitionLocation, UserProcDefinition
from qbparse.datatypes import (
    TYPE__NONE,
    TYPE_LONG,
    TYPE_SINGLE,
    TYPE_STRING,
    Parameter,
    TypeSignature,
)
from qbparse.symbols import Procedure
from qbparse.tests.helpers import Ast, parse_clean


def test_no_params():
    prog = parse_clean("""
        sub s
            print "hi"
        end sub
        function f
            print "bye"
        end function""")

    assert prog.globals.find_procedure("s") == Procedure(
        "s",
        [
            UserProcDefinition(
                "s", TypeSignature(ret=TYPE__NONE, params=[]), [Ast(Print)]
            )
        ],
    )
    assert prog.globals.find_procedure("f") == Procedure(
        "f",
        [
            UserProcDefinition(
                "f", TypeSignature(ret=TYPE_SINGLE, params=[]), [Ast(Print)]
            )
        ],
    )
    assert prog.main == Ast(
        UserProcDefinition,
        "_main",
        TypeSignature(ret=TYPE__NONE, params=[]),
        [Ast(ProcDefinitionLocation), Ast(ProcDefinitionLocation)],
    )


def test_mismatch_keyword_ok():
    parse_clean("sub s: end function : function f : end sub")


def test_sub_before_main():
    prog = parse_clean("""
        sub s
            print "hi"
        end sub
        x = 1""")
    assert prog.globals.find_procedure("s") is not None
    assert prog.main.find(Assignment) is not None


def test_sub_after_main():
    prog = parse_clean("""
        x = 1
        sub s
            print "hi"
        end sub""")
    assert prog.globals.find_procedure("s") is not None
    assert prog.main.find(Assignment) is not None


def test_subs_main_interleaved():
    prog = parse_clean("""
        x = 1
        sub s
            print "hi"
        end sub
        x = 2
        function f: end function
        """)
    assert prog.globals.find_procedure("s") is not None
    assert prog.globals.find_procedure("f") is not None
    assert len(list(prog.main.find_all(Assignment))) == 2


def test_function_return_type():
    prog = parse_clean("function f: end function")
    proc = prog.globals.find_procedure("f")
    assert proc is not None
    assert proc.sigs()[0].ret == TYPE_SINGLE

    prog = parse_clean("function f&: end function")
    proc = prog.globals.find_procedure("f")
    assert proc is not None
    assert proc.sigs()[0].ret == TYPE_LONG


def test_sub_return_type_disallowed():
    assert parse("sub s%: end sub").diagnostics.has(diag.E_SUB_WITH_TYPE)


def test_in_use_name():
    assert parse("sub if: end sub").diagnostics.has(diag.E_NAME_IN_USE)
    assert parse("function f: end function: sub f: end sub").diagnostics.has(
        diag.E_NAME_IN_USE
    )


def test_one_param():
    prog = parse_clean("function f(a&) : end function")
    proc = prog.globals.find_procedure("f")
    assert proc is not None
    assert proc.impls[0].signature == TypeSignature(
        TYPE_SINGLE, [Parameter(TYPE_LONG, "a")]
    )


def test_multi_param():
    prog = parse_clean("sub s(a&, b, c$) : end sub")
    proc = prog.globals.find_procedure("s")
    assert proc is not None
    assert proc.impls[0].signature == TypeSignature(
        TYPE__NONE,
        [
            Parameter(TYPE_LONG, "a"),
            Parameter(TYPE_SINGLE, "b"),
            Parameter(TYPE_STRING, "c"),
        ],
    )


def test_param_name_in_user():
    # assert parse('function f(if) : end function').diagnostics.has(diag.E_NAME_IN_USE)
    assert parse("function f(f) : end function").diagnostics.has(diag.E_NAME_IN_USE)
