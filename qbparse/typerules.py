from __future__ import annotations
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from qbparse import Program

from qbparse.ast import (
    Assignment,
    Call,
    Cast,
    Constant,
    If,
    Node,
    Print,
    ProcDefinition,
    Var,
)
from qbparse.datatypes import TYPE__NONE, TYPE_STRING, Type, can_cast


class WalkContext:
    def __init__(self, program: Program):
        self.program = program
        self.current = self.program.main
        self.parent = self.program.main
        self.handlers: list[tuple[type[Node], Callable[[Any], Type | None]]] = [
            (ProcDefinition, self.proc_definition),
            (Var, self.var),
            (Call, self.call),
            (Cast, self.cast),
            (Assignment, self.assignment),
            (Constant, self.constant),
            (Print, self.kw_print),
            (If, self.kw_if),
        ]

    def add_error(self, text: str):
        self.program.errors.append(text)

    def start(self):
        for proc in self.program.globals.procedures.values():
            if proc.impl is None:
                continue
            self.evaluate(proc.impl)

    def evaluate(self, node: Node) -> Type:
        old_parent = self.parent
        self.parent = self.current
        result = None
        for kind, handler in self.handlers:
            if isinstance(node, kind):
                result = handler(node)
                break
        else:
            raise ValueError(f"Unhandled node {node}")
        self.current = self.parent
        self.parent = old_parent
        return result if result else TYPE__NONE

    def proc_definition(self, impl: ProcDefinition):
        for stmt in impl.statements:
            self.evaluate(stmt)
        return TYPE__NONE

    def var(self, node: Var):
        return node.target.type

    def call(self, node: Call):
        raise NotImplementedError()

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
        return TYPE__NONE

    def constant(self, node: Constant):
        return node.type

    def kw_print(self, node: Print):
        for arg in node.args:
            type = self.evaluate(arg)
            if not type.is_number() and type != TYPE_STRING:
                self.add_error(f"Cannot print expression of type {type}")
        return TYPE__NONE

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
        return TYPE__NONE


def typecheck(program: Program):
    ctx = WalkContext(program)
    ctx.start()
