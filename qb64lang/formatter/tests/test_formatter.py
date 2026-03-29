from .helpers import format_clean, format_text


def test_comment():
    assert format_clean("'") == "'"
    assert format_clean("'foo") == "'foo"
    assert format_clean("'foo\n") == "'foo\n"
    assert format_clean(" 'foo\n") == "'foo\n"


def test_remark():
    assert format_clean("rem") == "REM"
    assert format_clean("rem foo") == "REM foo"
    assert format_clean("rem   foo\n") == "REM   foo\n"
    assert format_clean(" Rem foo\n") == "REM foo\n"


def test_line_split():
    assert format_clean("x=1:x=2") == "x = 1: x = 2"
    assert format_clean("x=1::x=2") == "x = 1:: x = 2"
    assert format_clean(":x=1:x=2:") == ": x = 1: x = 2:"


def test_variable_case():
    assert format_clean("Foo! = 1: foo = 2") == "Foo! = 1: Foo = 2"
    assert format_clean("Foo& = 1: foo = 2") == "Foo& = 1: foo = 2"


def test_expr_parentheses():
    assert format_clean("print x*((3-1))/(2)") == "PRINT x * ((3 - 1)) / (2)"


def test_expr_infix():
    assert format_clean("print x+3 or 4 and 5^6") == "PRINT x + 3 OR 4 AND 5 ^ 6"


def test_expr_prefix():
    assert format_clean("print not 3") == "PRINT NOT 3"
    assert format_clean("print - 3") == "PRINT -3"
    assert format_clean("print not-3") == "PRINT NOT -3"
    assert format_clean("print - not 3") == "PRINT -NOT 3"
    assert format_clean("print -(3)") == "PRINT -(3)"


def test_expr_doublet_signs():
    assert format_clean("print 2--2") == "PRINT 2 - -2"
    assert format_clean("print 2-+2") == "PRINT 2 - 2"
    assert format_clean("print 2+-2") == "PRINT 2 + -2"
    assert format_clean("print 2+-+--+2") == "PRINT 2 + ---2"


def test_numbers():
    assert format_clean("print 1234") == "PRINT 1234"
    assert format_clean("print 1234&") == "PRINT 1234&"
    assert format_clean("print 12.34") == "PRINT 12.34"
    assert format_clean("print 12.34#") == "PRINT 12.34#"
    assert format_clean("print &hdead") == "PRINT &HDEAD"
    assert format_clean("print &hdead~&&") == "PRINT &HDEAD~&&"
    assert format_clean("print 1.2e-4") == "PRINT 1.2E-4"


def test_string():
    assert format_clean('Print "abc"') == 'PRINT "abc"'


def test_func_call():
    assert format_clean("print _autodisplay+1") == "PRINT _AUTODISPLAY + 1"
    assert format_clean('print lcase$("hello")') == 'PRINT LCASE$("hello")'
    assert format_clean('print left$("hello",123)') == 'PRINT LEFT$("hello", 123)'
    assert format_clean('print val("2")') == 'PRINT VAL("2")'


def test_sub_call():
    assert format_clean("_autodisplay") == "_AUTODISPLAY"
    assert format_clean("mkdir foo$") == "MKDIR foo$"
    assert format_clean("out a, b") == "OUT a, b"


def test_continue_on_lex_error():
    assert format_text("print !@hi") == "print !@hi"
    assert format_text("print ! @ hi") == "print ! @ hi"
    assert format_text("! @ hi") == "! @ hi"
    assert format_text("print x\nprint !hi\nprint y") == "PRINT x\nprint !hi\nPRINT y"


def test_continue_on_parse_error():
    assert format_text("x = 1 2 3") == "x = 1 2 3"
    assert format_text("print next") == "print next"
    assert format_text("if 1\nprint 2\nend if") == "if 1\nprint 2\nend if"
    assert format_text("x=1 2 3\ny=4") == "x=1 2 3\ny = 4"
    assert format_text("x=1 2 3\nx=1 2 3\ny=4") == "x=1 2 3\nx=1 2 3\ny = 4"
    assert (
        format_text("for i = 1 to 3\nprint next\nnext i")
        == "FOR i = 1 TO 3\nprint next\nNEXT i"
    )


def test_semantic_errors_formatted():
    assert format_text("x$=3") == "x$ = 3"
    assert format_text("if Foo$ then print foo$") == "IF Foo$ THEN PRINT Foo$"


def test_compound_type_definition():
    assert (
        format_clean("type foo\nA as long\nas string b,c\nend type")
        == "TYPE foo\n    A AS LONG\n    AS STRING b, c\nEND TYPE"
    )


def test_field_access():
    assert (
        format_clean("""
        type foo
        Bar as long
        end type
        dim Baz as foo
        print baz.bar
        """)
        == """
TYPE foo
    Bar AS LONG
END TYPE
DIM Baz AS foo
PRINT Baz.Bar
"""
    )


def test_dim():
    assert format_clean("dim a(2,3),b$(1 to 5)") == "DIM a(2, 3), b$(1 TO 5)"


def test_array_access():
    assert (
        format_clean("dim Foo(2,3) : print Foo(1,2)")
        == "DIM Foo(2, 3): PRINT Foo(1, 2)"
    )


def test_static_dynamic_metacommands_comment():
    assert (
        format_clean("""
'$dynamic
'$Static foobar $DYnamic
'This is not $static or $dynamic
print '$dynamic
""")
        == """
'$DYNAMIC
'$STATIC foobar $DYNAMIC
'This is not $static or $dynamic
PRINT '$DYNAMIC
"""
    )


def test_static_dynamic_metacommands_remark():
    assert (
        format_clean("""
rem $dynamic
rem $Static foobar $DYnamic
rem This is not $static or $dynamic
print rem $dynamic
""")
        == """
REM $DYNAMIC
REM $STATIC foobar $DYNAMIC
REM This is not $static or $dynamic
PRINT REM $DYNAMIC
"""
    )


def test_hex():
    assert format_clean("print hex$(3)") == "PRINT HEX$(3)"
