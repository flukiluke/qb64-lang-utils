from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any

import qbparse.diagnostics as diag

if TYPE_CHECKING:
    from qbparse import Program

from qbparse.ast import (
    Assignment,
    BuiltinProcDefinition,
    Call,
    Cast,
    Constant,
    Expr,
    For,
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
    TYPE_ANY,
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
            (For, self.kw_for),
        ]

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
        for arg in node.args:
            self.evaluate(arg)
        if node.target.name == "=" or node.target.name == "<>":
            node.impl = self._equality_call(node)
        elif len(node.target.impls) == 1:
            node.impl = self._single_impl_call(node)
        else:
            node.impl = self._find_impl_match(node)
        if node.impl is None:
            return TYPE__NONE
        new_args = list[Expr]()
        for arg, param in zip(node.args, node.impl.signature.params):
            if arg.expr_type != param.type and param.type != TYPE_ANY:
                new_args.append(Cast(arg, param.type))
            else:
                new_args.append(arg)
        node.args = new_args
        return node.impl.signature.ret

    def _equality_call(self, node: Call):
        """
        The = and <> are implicitly defined for all types, so they don't have an
        explicit list of impls. As long as we can cast both arguments to the same
        type the operation is OK.
        """
        left = node.args[0].expr_type
        right = node.args[1].expr_type
        if left == right:
            pass
        elif not left.is_number() or not right.is_number():
            self.program.diagnostics.create(
                diag.E_NO_MATCHING_OVERLOAD,
                node,
                node.target.name + " operator",
                left.name + " and " + right.name,
            )
            return None
        elif can_safely_cast(left, right):
            node.args[0] = Cast(node.args[0], right)
        elif can_safely_cast(right, left):
            node.args[1] = Cast(node.args[1], left)
        else:
            node.args = [
                Cast(node.args[0], TYPE__FLOAT),
                Cast(node.args[1], TYPE__FLOAT),
            ]
        return node.target.impls[0]

    def _single_impl_call(self, node: Call):
        params = node.target.impls[0].signature.params
        if len(node.args) < len(params):
            self.program.diagnostics.create(
                diag.E_NOT_ENOUGH_ARGUMENTS,
                node,
                node.target.name,
                len(params),
                len(node.args),
            )
            return None
        elif len(node.args) > len(params):
            self.program.diagnostics.create(
                diag.E_TOO_MANY_ARGUMENTS,
                node,
                node.target.name,
                len(params),
                len(node.args),
            )
            return None
        args_ok = True
        for param, arg in zip(params, node.args):
            if not can_cast(param.type, arg.expr_type):
                self.program.diagnostics.create(
                    diag.E_ARG_TYPE_MISMATCH, arg, arg.expr_type, param
                )
                args_ok = False
        if args_ok:
            return node.target.impls[0]
        return None

    def _find_impl_match(self, node: Call):
        """
        Return the impl whose type signature best match the argument types,
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
        version that doesn't lose data is picked. 3 handles passing floats to
        integer-only functions like bitwise operators. 4 is a fallback if a cast is
        inevitable.
        """
        impls = node.target.impls
        arg_types = [arg.expr_type for arg in node.args]
        compatibles = [
            impl
            for impl in impls
            if self._impl_is_compatible(impl, arg_types, lossless=False)
        ]
        if len(compatibles) == 0:
            self.program.diagnostics.create(
                diag.E_NO_MATCHING_OVERLOAD,
                node,
                node.target.name,
                ", ".join([t.name for t in arg_types]),
            )
            return None
        if len(compatibles) == 1:
            return compatibles[0]
        for impl in compatibles:
            if self._impl_is_compatible(impl, arg_types, lossless=True):
                return impl
        arg_types = list(
            map(lambda t: TYPE__INTEGER64 if isinstance(t, FloatType) else t, arg_types)
        )
        for impl in compatibles:
            if self._impl_is_compatible(impl, arg_types, lossless=True):
                return impl
        return compatibles[-1]

    def _impl_is_compatible(
        self, impl: ProcDefinition, arg_types: Sequence[Type], lossless: bool
    ):
        if len(impl.signature.params) != len(arg_types):
            return False
        check_func = can_safely_cast if lossless else can_cast
        for param, arg in zip(impl.signature.params, arg_types):
            if not check_func(arg, param.type):
                return False
        return True

    def cast(self, node: Cast):
        type = self.evaluate(node.expr)
        if not can_cast(type, node.type):
            self.program.diagnostics.create(
                diag.E_ARG_TYPE_MISMATCH, node, type.name, node.type.name
            )
        return node.type

    def assignment(self, node: Assignment):
        rtype = self.evaluate(node.rval)
        ltype = self.evaluate(node.lval)
        if not can_cast(rtype, ltype):
            self.program.diagnostics.create(
                diag.E_ASSIGNMENT_MISMATCH, node, rtype.name, ltype.name
            )
        elif rtype != ltype:
            node.rval = Cast(node.rval, ltype)

    def constant(self, node: Constant):
        return node.type

    def kw_print(self, node: Print):
        for arg in node.args:
            type = self.evaluate(arg)
            if not type.is_number() and type != TYPE_STRING:
                self.program.diagnostics.create(
                    diag.E_UNPRINTABLE_TYPE, node, type.name
                )

    def kw_if(self, node: If):
        type = self.evaluate(node.guard)
        if not type.is_number():
            self.program.diagnostics.create(diag.E_NON_NUMERIC_CONDITION, node.guard)
        for stmt in node.true_branch:
            self.evaluate(stmt)
        for stmt in node.false_branch:
            self.evaluate(stmt)
        for condition, stmts in node.elseifs:
            if not self.evaluate(condition).is_number():
                self.program.diagnostics.create(diag.E_NON_NUMERIC_CONDITION, condition)
            for stmt in stmts:
                self.evaluate(stmt)

    def kw_loop(self, node: Loop):
        type = self.evaluate(node.guard)
        if not type.is_number():
            self.program.diagnostics.create(diag.E_NON_NUMERIC_CONDITION, node.guard)
        for stmt in node.block:
            self.evaluate(stmt)

    def kw_for(self, node: For):
        var_type = self.evaluate(node.iterator)
        if not var_type.is_number():
            self.program.diagnostics.create(diag.E_NON_NUMERIC_VARIABLE, node.iterator)
        start_type = self.evaluate(node.start_value)
        if not start_type.is_number():
            self.program.diagnostics.create(diag.E_NON_NUMERIC_EXPR, node.start_value)
        end_type = self.evaluate(node.end_value)
        if not end_type.is_number():
            self.program.diagnostics.create(diag.E_NON_NUMERIC_EXPR, node.end_value)
        step_type = self.evaluate(node.step)
        if not step_type.is_number():
            self.program.diagnostics.create(diag.E_NON_NUMERIC_EXPR, node.step)
        if start_type != var_type:
            node.start_value = Cast(node.start_value, var_type)
        if end_type != var_type:
            node.end_value = Cast(node.end_value, var_type)
        if step_type != var_type:
            node.step = Cast(node.step, var_type)
        for stmt in node.block:
            self.evaluate(stmt)


def typecheck(program: Program):
    ctx = WalkContext(program)
    ctx.start()
