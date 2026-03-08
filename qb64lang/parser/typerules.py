from collections.abc import Sequence
from typing import TYPE_CHECKING

from . import diagnostics as diag

if TYPE_CHECKING:
    from . import Program

from .ast import (
    Assignment,
    AstWalk,
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
    SetReturn,
    Var,
)
from .datatypes import (
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


class TypePass(AstWalk[None | Type]):
    def start(self):
        for proc in self.program.symbols.procedures.values():
            for impl in proc.impls:
                self.evaluate(impl)

    def evaluate(self, node: Node):
        result = super().evaluate(node)
        if result is None:
            result = TYPE__NONE
        if isinstance(node, Expr):
            node.expr_type = result
        return result

    def proc_definition(self, node: ProcDefinition):
        for stmt in node.statements:
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
                new_args.append(Cast.wrap(arg, param.type))
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
            node.args[0] = Cast.wrap(node.args[0], right)
        elif can_safely_cast(right, left):
            node.args[1] = Cast.wrap(node.args[1], left)
        else:
            node.args = [
                Cast.wrap(node.args[0], TYPE__FLOAT),
                Cast.wrap(node.args[1], TYPE__FLOAT),
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
            2) Filter to only impls that are a sub/function as required.
                a) If there are no compatibles, return None.
                b) If there is exactly 1 compatible, return it.
            3) Of all compatible impls, return the first one where all casts are
            lossless. If no impl has all lossless casts, continue to 3.
            4) Round all float arguments to the largest signed integral type
            (i.e. _integer64) and return the first compatible impl that
            now has all lossless casts.
            5) If still no impl has all lossless casts, return the last one.
        Rule 2b is the usual case for simple procedures. 3 allows overloaded
        functions to be listed in order of increasing type width and the narrowest
        version that doesn't lose data is picked. 4 handles passing floats to
        integer-only functions like bitwise operators. 5 is a fallback if a cast is
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
        if node.style == Call.Style.STATEMENT:
            compatibles = [
                impl for impl in compatibles if impl.signature.ret == TYPE__NONE
            ]
        else:
            compatibles = [
                impl for impl in compatibles if impl.signature.ret != TYPE__NONE
            ]
        if len(compatibles) == 0:
            self.program.diagnostics.create(
                diag.E_EXPECTED_SUB_NOT_FUNCTION
                if node.style == Call.Style.STATEMENT
                else diag.E_EXPECTED_FUNCTION_NOT_SUB,
                node,
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
            node.rval = Cast(
                node.rval,
                ltype,
                lex_start=node.rval.lex_start,
                lex_end=node.rval.lex_end,
            )

    def constant(self, node: Constant):
        return node.type

    def kw_print(self, node: Print):
        using = False
        for arg in node.args:
            if isinstance(arg, Expr):
                type = self.evaluate(arg)
                if using:
                    if type != TYPE_STRING:
                        self.program.diagnostics.create(diag.E_USING_NON_STRING, node)
                    using = False
                if not type.is_number() and type != TYPE_STRING:
                    self.program.diagnostics.create(
                        diag.E_UNPRINTABLE_TYPE, node, type.name
                    )
            elif arg == Print.Element.USING:
                using = True

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
        for guard in node.top_guard, node.bottom_guard:
            if guard:
                type = self.evaluate(guard)
                if not type.is_number():
                    self.program.diagnostics.create(diag.E_NON_NUMERIC_CONDITION, guard)
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
            node.start_value = Cast.wrap(node.start_value, var_type)
        if end_type != var_type:
            node.end_value = Cast.wrap(node.end_value, var_type)
        if step_type != var_type:
            node.step = Cast.wrap(node.step, var_type)
        for stmt in node.block:
            self.evaluate(stmt)

    def set_return(self, node: SetReturn):
        func_type = node.impl.signature.ret
        expr_type = self.evaluate(node.value)
        if not can_cast(expr_type, func_type):
            self.program.diagnostics.create(
                diag.E_RETURN_MISMATCH, node, expr_type.name, func_type.name
            )
        elif func_type != expr_type:
            node.value = Cast.wrap(node.value, func_type)


def typecheck(program: "Program"):
    TypePass(program).start()
