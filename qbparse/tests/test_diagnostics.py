from qbparse import parse
from qbparse.ast import If, Print
from qbparse.diagnostics import E_UNEXPECTED_ITEM, DiagnosticStore
from qbparse.lexer import Lexer
from qbparse.store import SymbolStore
from qbparse.tests.helpers import Ast


def testBadCharacter():
    lex = Lexer(SymbolStore(), DiagnosticStore())
    lex.input('@ "hello"')
    print(list(lex))
    assert False


def testLimitFloat():
    lex = Lexer(SymbolStore(), DiagnosticStore())
    lex.input("? 1e200")
    print(list(lex))
    assert False


def testLimitBaseImplicit():
    lex = Lexer(SymbolStore(), DiagnosticStore())
    lex.input("? &h010000000000000000")
    print(list(lex))
    assert False


def testLimitBaseExplicit():
    lex = Lexer(SymbolStore(), DiagnosticStore())
    lex.input("? &b10`")
    print(list(lex))
    assert False


def test_bad_expr_drops_line():
    prog = parse("""
        if x = 2 then
            ? 23 * 1
            ? 2 + / 2
            ? 10 - 3
        end if
    """)
    assert prog.diagnostics.has(E_UNEXPECTED_ITEM)
    assert prog.main.find(If) == Ast(If, true_branch=[Ast(Print), Ast(Print)])
