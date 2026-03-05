from .helpers import format_clean


def test_for():
    assert (
        format_clean("for i=1 to 3\nprint i\nnext i")
        == "FOR i = 1 TO 3\n    PRINT i\nNEXT i"
    )


def test_for_combined():
    assert (
        format_clean(
            """
for i = 1 to 3
for j = 1 to 3
print i, j
next j, i"""
        )
        == """
FOR i = 1 TO 3
    FOR j = 1 TO 3
        PRINT i, j
NEXT j, i"""
    )


def test_single_line_if():
    assert (
        format_clean("if x = 1 then print x\nprint y")
        == "IF x = 1 THEN PRINT x\nPRINT y"
    )
    assert (
        format_clean("if x = 1 then print x else print y\nprint z")
        == "IF x = 1 THEN PRINT x ELSE PRINT y\nPRINT z"
    )


def test_if_then():
    assert (
        format_clean("if x = 1 then\nprint x\nend if")
        == "IF x = 1 THEN\n    PRINT x\nEND IF"
    )


def test_if_then_else():
    assert (
        format_clean(
            """
if x = 1 then
print x
elseif x = 2 then
print z
print a
elseif x = 3 then print b
print c
else
print y
endif"""
        )
        == """
IF x = 1 THEN
    PRINT x
ELSEIF x = 2 THEN
    PRINT z
    PRINT a
ELSEIF x = 3 THEN PRINT b
    PRINT c
ELSE
    PRINT y
END IF"""
    )


def test_nested_if():
    assert (
        format_clean(
            """
if x = 1 then
if y = 1 then print y else print x
print z
end if"""
        )
        == """
IF x = 1 THEN
    IF y = 1 THEN PRINT y ELSE PRINT x
    PRINT z
END IF"""
    )


def test_loops():
    assert (
        format_clean("while x > 1\nprint x\nwend") == "WHILE x > 1\n    PRINT x\nWEND"
    )
    assert (
        format_clean("do while x > 1\nprint x\nloop")
        == "DO WHILE x > 1\n    PRINT x\nLOOP"
    )


def test_subroutines():
    assert (
        format_clean("sub s\nprint 1\nprint 2\nend sub")
        == "SUB s\n    PRINT 1\n    PRINT 2\nEND SUB"
    )
    assert (
        format_clean("function f\nprint 1\nprint 2\nend function")
        == "FUNCTION f\n    PRINT 1\n    PRINT 2\nEND FUNCTION"
    )
    assert format_clean("declare function f\nprint 1") == "DECLARE FUNCTION f\nPRINT 1"
