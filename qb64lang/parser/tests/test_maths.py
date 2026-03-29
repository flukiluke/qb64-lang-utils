from .helpers import parse_clean


def test_abs():
    parse_clean("print abs(x&)")
    parse_clean("print abs(x!)")


def test_bitwise():
    parse_clean("print x& and y&")
    parse_clean("print x& eqv y&")
    parse_clean("print x& imp y&")
    parse_clean("print not x&&")
    parse_clean("print x& or y&")
    parse_clean("print x& xor y&")


def test_trig():
    parse_clean("print atn(x!)")
    parse_clean("print cos(x!)")


def test_logarithms():
    parse_clean("print exp(x!)")
    parse_clean("print log(x!)")


def test_arithmetic4():
    parse_clean("print 1 + 2")
    parse_clean("print 1 - 2")
    parse_clean("print 1 / 2")
    parse_clean("print 1 * 2")
