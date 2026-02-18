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


def test_variable():
    assert format_clean("Foo! = 1: foo = 2") == "Foo! = 1: Foo = 2"
