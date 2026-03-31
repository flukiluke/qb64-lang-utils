from ..ast import ArrayAccess, Call, Constant
from .helpers import Ast, builtin_proc, parse_clean


def test_abs_sgn():
    assert parse_clean("a = abs(x&)").main.find(Call) is not None
    assert parse_clean("a = abs(x!)").main.find(Call) is not None
    assert parse_clean("a = sgn(x&)").main.find(Call) is not None
    assert parse_clean("a = sgn(x!)").main.find(Call) is not None


def test_bitwise():
    assert parse_clean("a = x& and y&").main.find(Call) is not None
    assert parse_clean("a = x& eqv y&").main.find(Call) is not None
    assert parse_clean("a = x& imp y&").main.find(Call) is not None
    assert parse_clean("a = not x&&").main.find(Call) is not None
    assert parse_clean("a = x& or y&").main.find(Call) is not None
    assert parse_clean("a = x& xor y&").main.find(Call) is not None


def test_trig():
    assert parse_clean("a = atn(x!)").main.find(Call) is not None
    assert parse_clean("a = cos(x!)").main.find(Call) is not None
    assert parse_clean("a = sin(x!)").main.find(Call) is not None
    assert parse_clean("a = tan(x!)").main.find(Call) is not None


def test_log_pow_roots():
    assert parse_clean("a = exp(x!)").main.find(Call) is not None
    assert parse_clean("a = log(x!)").main.find(Call) is not None
    assert parse_clean("a = sqr(x!)").main.find(Call) is not None


def test_arithmetic4():
    assert parse_clean("a = 1 + 2").main.find(Call) is not None
    assert parse_clean("a = 1 - 2").main.find(Call) is not None
    assert parse_clean("a = 1 / 2").main.find(Call) is not None
    assert parse_clean("a = 1 * 2").main.find(Call) is not None


def test_hex():
    assert parse_clean("print hex$(3)").main.find(Call) == Ast(
        Call, args=[Ast(Constant, 3)]
    )
    assert parse_clean("print hex(3)").main.find(ArrayAccess) is not None


def test_end_command():
    # Special enough to need a dedicated test because of the
    # conflict with the syntactic structure.
    prog = parse_clean("end \n end 1")
    assert list(prog.main.find_all(Call)) == [
        Ast(Call, builtin_proc("end")),
        Ast(Call, builtin_proc("end"), [Ast(Constant, 1)]),
    ]
