from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from qbparse import Program

from qbparse.ast import (
    Assignment,
    BuiltinProcDefinition,
    Call,
    Cast,
    Constant,
    Expr,
    If,
    Loop,
    Node,
    Print,
    ProcDefinition,
    UserProcDefinition,
    Var,
)
from qbparse.datatypes import (
    TYPE__FLOAT,
    TYPE__INTEGER64,
    TYPE__NONE,
    TYPE_STRING,
    FloatType,
    Type,
    can_cast,
    can_safely_cast,
)


class WalkContext:
    def __init__(self, program: Program):
        self.program = program
        self.current = self.program.main
        self.parent = self.program.main
        self.expr_handlers: list[tuple[type[Expr], Callable[[Any], Type]]] = [
            (Var, self.var),
            (Call, self.call),
            (Cast, self.cast),
            (Constant, self.constant),
        ]
        self.stmt_handlers: list[tuple[type[Node], Callable[[Any], Type | None]]] = [
            (BuiltinProcDefinition, lambda _: TYPE__NONE),
            (UserProcDefinition, self.proc_definition),
            (Assignment, self.assignment),
            (Print, self.kw_print),
            (If, self.kw_if),
            (Loop, self.kw_loop),
        ]

    def add_error(self, text: str):
        self.program.errors.append(text)

    def start(self):
        for proc in self.program.globals.procedures.values():
            for impl in proc.impls:
                self.evaluate(impl)

    def evaluate(self, node: Node):
        old_parent = self.parent
        self.parent = self.current
        result = None
        for kind, handler in (
            self.expr_handlers if isinstance(node, Expr) else self.stmt_handlers
        ):
            if isinstance(node, kind):
                result = handler(node)
                if result is None:
                    result = TYPE__NONE
                break
        else:
            raise ValueError(f"Unhandled node {node}")
        if isinstance(node, Expr):
            node.expr_type = result
        self.current = self.parent
        self.parent = old_parent
        return result

    def proc_definition(self, impl: UserProcDefinition):
        for stmt in impl.statements:
            self.evaluate(stmt)

    def var(self, node: Var):
        return node.target.type

    def call(self, node: Call):
        if node.target.name == "=" or node.target.name == "<>":
            return self._equality_call(node)
        arg_types = [self.evaluate(arg) for arg in node.args]
        node.impl = _find_impl_match(node.target.impls, arg_types)
        if node.impl is None:
            self.add_error("Cannot resolve function call types")
            return TYPE__NONE
        new_args = list[Expr]()
        for arg, param_type in zip(node.args, node.impl.signature.params):
            if arg.expr_type != param_type:
                new_args.append(Cast(arg, param_type))
            else:
                new_args.append(arg)
        node.args = new_args
        return node.impl.signature.ret

    def _equality_call(self, node: Call):
        if len(node.args) != 2:
            self.add_error(node.target.name + " operator must have 2 arguments")
            return TYPE__NONE
        node.impl = node.target.impls[0]
        left = self.evaluate(node.args[0])
        right = self.evaluate(node.args[1])
        if left == right:
            pass
        elif not left.is_number() or not right.is_number():
            self.add_error(f"Cannot apply {node.target.name} operator to {left} and {right}")
            return TYPE__NONE
        elif can_safely_cast(left, right):
            node.args[0] = Cast(node.args[0], right)
        elif can_safely_cast(right, left):
            node.args[1] = Cast(node.args[1], left)
        else:
            node.args = [Cast(node.args[0], TYPE__FLOAT), Cast(node.args[1], TYPE__FLOAT)]
        return node.impl.signature.ret

    def cast(self, node: Cast):
        type = self.evaluate(node.expr)
        if not can_cast(type, node.type):
            self.add_error(f"Cannot convert expression from {type} to {node.type}")
        return node.type

    def assignment(self, node: Assignment):
        rtype = self.evaluate(node.rval)
        ltype = self.evaluate(node.lval)
        if not can_cast(rtype, ltype):
            self.add_error(
                f"Cannot assign expression of type {rtype} to variable of type {ltype}"
            )
        elif rtype != ltype:
            node.rval = Cast(node.rval, ltype)

    def constant(self, node: Constant):
        return node.type

    def kw_print(self, node: Print):
        for arg in node.args:
            type = self.evaluate(arg)
            if not type.is_number() and type != TYPE_STRING:
                self.add_error(f"Cannot print expression of type {type}")

    def kw_if(self, node: If):
        type = self.evaluate(node.guard)
        if not type.is_number():
            self.add_error("Condition must be a numeric expression")
        for stmt in node.true_branch:
            self.evaluate(stmt)
        for stmt in node.false_branch:
            self.evaluate(stmt)
        for condition, stmts in node.elseifs:
            if not self.evaluate(condition).is_number():
                self.add_error("Condition must be a numeric expression")
            for stmt in stmts:
                self.evaluate(stmt)

    def kw_loop(self, node: Loop):
        type = self.evaluate(node.guard)
        if not type.is_number():
            self.add_error("Loop guard must be a numeric expression")
        for stmt in node.block:
            self.evaluate(stmt)


def typecheck(program: Program):
    ctx = WalkContext(program)
    ctx.start()


def _find_impl_match(impls: list[ProcDefinition], arg_types: list[Type]):
    """
    Return the impl whose type signature best match the arg_types given,
    or None if no impl matches.
    The algorithm is:
        1) Select all compatible impls. An impl is compatible if all arguments
           can be cast (even with loss) to the expected type.
            a) If there are no compatibles, return None.
            b) If there is exactly 1 compatible, return it.
        2) Of all compatible impls, return the first one where all casts are
           lossless. If no impl has all lossless casts, continue to 3.
        3) Round all float arguments to the largest signed integral type
           (i.e. _integer64) and return the first compatible impl that
           now has all lossless casts.
        4) If still no impl has all lossless casts, return the last one.
    Rule 1b is the usual case for simple procedures. 2 allows overloaded
    functions to be listed in order of increasing type width and the narrowest
    version that doesn't lose data is picked. 3 handles passing floats to integer-only
    functions like bitwise operators. 4 is a fallback if a cast is inevitable.
    """
    compatibles = [
        impl for impl in impls if _impl_is_compatible(impl, arg_types, lossless=False)
    ]
    if len(compatibles) == 0:
        return None
    if len(compatibles) == 1:
        return compatibles[0]
    for impl in compatibles:
        if _impl_is_compatible(impl, arg_types, lossless=True):
            return impl
    arg_types = list(
        map(lambda t: TYPE__INTEGER64 if isinstance(t, FloatType) else t, arg_types)
    )
    for impl in compatibles:
        if _impl_is_compatible(impl, arg_types, lossless=True):
            return impl
    return compatibles[-1]


def _impl_is_compatible(impl: ProcDefinition, arg_types: list[Type], lossless: bool):
    if len(impl.signature.params) != len(arg_types):
        return False
    check_func = can_safely_cast if lossless else can_cast
    for param, arg in zip(impl.signature.params, arg_types):
        if not check_func(arg, param):
            return False
    return True
