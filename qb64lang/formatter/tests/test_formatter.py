from .helpers import format_clean


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
