from .. import diagnostics as diag
from .. import parse
from ..ast import ArrayAccess, Assignment, Print, Var
from ..datatypes import TYPE_INTEGER, TYPE_SINGLE, TYPE_STRING
from .helpers import Ast, parse_clean


def test_unsigiled_scalar():
    """
    Unsigiled variable is accessed without sigil or with matching sigil.
    """
    prog = parse_clean("dim x as string : x = x$")
    var = prog.symbols.find_variable("x", None)
    assert prog.main.find(Assignment) == Ast(Assignment, Ast(Var, var), Ast(Var, var))


def test_unsigiled_scalar_with_sigiled_scalar():
    """
    Differently sigiled variable is separate from unsigiled variable.
    """
    prog = parse_clean("dim x as string : print x%, x")
    var_int = prog.symbols.find_variable("x", TYPE_INTEGER)
    var_str = prog.symbols.find_variable("x", TYPE_STRING)
    assert prog.main.find(Print) == Ast(
        Print, [Ast(Var, var_int), Print.Element.COMMA, Ast(Var, var_str)]
    )


def test_unsigiled_array():
    """
    Unsigiled array is accessed without sigil or with matching sigil.
    """
    prog = parse_clean("dim x(3) as string : x(1) = x$(2)")
    var = prog.symbols.find_variable("x", None, as_array=True)
    assert prog.main.find(Assignment) == Ast(
        Assignment, Ast(ArrayAccess, Ast(Var, var)), Ast(ArrayAccess, Ast(Var, var))
    )


def test_unsigiled_array_with_sigiled_array():
    """
    Differently sigiled array is separate from unsigiled array.
    """
    prog = parse_clean("dim x(3) as string : print x%(2), x(1)")
    var_int = prog.symbols.find_variable("x", TYPE_INTEGER, as_array=True)
    var_str = prog.symbols.find_variable("x", TYPE_STRING, as_array=True)
    assert prog.main.find(Print) == Ast(
        Print,
        [
            Ast(ArrayAccess, Ast(Var, var_int)),
            Print.Element.COMMA,
            Ast(ArrayAccess, Ast(Var, var_str)),
        ],
    )


def test_unsigiled_array_scalar_separate():
    """
    Unsigiled arrays and scalars can co-exist.
    """
    prog = parse_clean("dim x(3) as string , x as string : print x(1), x")
    var_arr = prog.symbols.find_variable("x", TYPE_STRING, as_array=True)
    var_scalar = prog.symbols.find_variable("x", TYPE_STRING, as_array=False)
    assert prog.main.find(Print) == Ast(
        Print,
        [
            Ast(ArrayAccess, Ast(Var, var_arr)),
            Print.Element.COMMA,
            Ast(Var, var_scalar),
        ],
    )


def test_multiple_unsigiled_scalar_prohibited():
    """
    Cannot have multiple scalars both unsigiled.
    """
    assert parse("dim x as long : dim x as integer").diagnostics.has(diag.E_DUPE_DIM)


def test_multiple_unsigiled_array_prohibited():
    """
    Cannot have multiple arrays both unsigiled.
    """
    assert parse("dim x(2) as long : dim x(3) as integer").diagnostics.has(
        diag.E_DUPE_DIM
    )


def test_dim_sigiled_over_dim_unsigned():
    prog = parse_clean("dim x as long : dim x%: print x%")
    var = prog.symbols.find_variable("x", TYPE_INTEGER)
    assert prog.main.find(Print) == Ast(Print, [Ast(Var, var)])


def test_default_unsigiled_scalar_type():
    """
    Default unsigiled type can be accessed as sigiled scalar.
    """
    prog = parse_clean("print x, x!")
    var = prog.symbols.find_variable("x", None)
    assert prog.main.find(Print) == Ast(
        Print,
        [
            Ast(Var, var),
            Print.Element.COMMA,
            Ast(Var, var),
        ],
    )


def test_default_unsigiled_array_type():
    """
    Default unsigiled type can be accessed as sigiled array.
    """
    prog = parse_clean("print x(2), x!(3)")
    var = prog.symbols.find_variable("x", None, as_array=True)
    assert prog.main.find(Print) == Ast(
        Print,
        [
            Ast(ArrayAccess, Ast(Var, var)),
            Print.Element.COMMA,
            Ast(ArrayAccess, Ast(Var, var)),
        ],
    )


def test_default_sigil_is_unsigiled():
    """
    Variables explicitly with the default sigil can be accessed unsigiled.
    """
    prog = parse_clean("x! = x")
    var = prog.symbols.find_variable("x", TYPE_SINGLE)
    assert prog.main.find(Assignment) == Ast(Assignment, Ast(Var, var), Ast(Var, var))


def test_explicit_over_unsigiled():
    """
    Explicitly defining unsigiled variable shadows unsigiled access to
    sigiled default type variable.
    """
    prog = parse_clean("dim x! : dim x as integer : print x")
    var = prog.symbols.find_variable("x", TYPE_INTEGER)
    assert prog.main.find(Print) == Ast(Print, [Ast(Var, var)])


def test_explicit_over_implicit_unsigiled():
    """
    Explicitly defining unsigiled variable shadows unsigiled access to
    implicitly declared default type variable.
    """
    prog = parse_clean("x = 3 : dim x as integer : print x")
    var = prog.symbols.find_variable("x", TYPE_INTEGER)
    assert prog.main.find(Print) == Ast(Print, [Ast(Var, var)])


def test_dim_after_implicit_sigiled_prohibited():
    """
    Explicitly defining a variable of the same type as a sigiled
    implicitly declared variable is prohibited.
    """
    assert parse("x% = 3 : dim x as integer").diagnostics.has(diag.E_DUPE_DIM)
