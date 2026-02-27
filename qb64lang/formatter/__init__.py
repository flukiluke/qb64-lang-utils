import contextlib
import re
from collections.abc import Generator
from enum import Enum, auto

from qb64lang.parser.ast import Assignment, Call, ProcDeclaration

from ..parser import Program
from ..parser.ast import (
    KEYWORDS,
    AstWalk,
    Cast,
    Constant,
    Dim,
    For,
    If,
    Loop,
    Node,
    Print,
    ProcDefinitionLocation,
    Procedure,
    SetReturn,
    Var,
    Variable,
)
from ..parser.datatypes import TYPE__NONE, Type
from ..parser.diagnostics import DiagnosticError, DiagnosticStore
from ..parser.lexer import Lexer
from ..parser.ply import LexToken


class Capitalisation(Enum):
    NONE = auto()
    CAMEL = auto()
    UPPER = auto()


class FormatPass(AstWalk[str]):
    def start(self):
        result = ""
        for stmt in self.program.main.statements:
            result += self.evaluate(stmt)
        return result

    def assignment(self, node: Assignment):
        return self.evaluate(node.lval) + " = " + self.evaluate(node.rval)

    def call(self, node: Call):
        result = ""
        match node.style:
            case Call.Style.FUNCTION:
                if not node.args:
                    result = node.target.source_name
                else:
                    result = (
                        node.target.source_name
                        + "("
                        + ", ".join([self.evaluate(arg) for arg in node.args])
                        + ")"
                    )
            case Call.Style.INFIX:
                result = (
                    self.evaluate(node.args[0])
                    + " "
                    + node.target.source_name
                    + " "
                    + self.evaluate(node.args[1])
                )
            case Call.Style.PREFIX if node.target.name == "-":
                result = node.target.source_name + self.evaluate(node.args[0])
            case Call.Style.PREFIX:
                result = node.target.source_name + " " + self.evaluate(node.args[0])
            case Call.Style.STATEMENT:
                if not node.args:
                    result = node.target.source_name
                else:
                    result = node.target.source_name + ", ".join(
                        [self.evaluate(arg) for arg in node.args]
                    )
        return "(" * node.parens + result + ")" * node.parens

    def cast(self, node: Cast):
        return self.evaluate(node.expr)

    def constant(self, node: Constant):
        repr = node.get_source_repr(self.program.input)
        if node.parens:
            return "(" + repr + ")"
        return repr

    def kw_dim(self, node: Dim):
        result = "ReDim " if node.is_redim else "Dim "
        if node.leading_type is not None:
            result += "As " + node.leading_type.source_name + " "
        result += ", ".join([var.source_name for var in node.variables])
        return result

    def kw_for(self, node: For):
        var = node.iterator.get_source_repr(self.program.input)
        result = "For "
        result += var + " = "
        result += self.evaluate(node.start_value) + " To "
        result += self.evaluate(node.end_value) + " Step "
        result += self.evaluate(node.step)
        for stmt in node.block:
            result += self.evaluate(stmt)
        result += "Next " + var
        return result

    def kw_if(self, node: If):
        result = "If "
        result += self.evaluate(node.guard)
        result += " Then "
        for stmt in node.true_branch:
            result += self.evaluate(stmt)
        for elseif in node.elseifs:
            result += "ElseIf " + self.evaluate(elseif[0]) + " Then "
            for stmt in elseif[1]:
                result += self.evaluate(stmt)
        if node.false_branch:
            result += " Else "
            for stmt in node.false_branch:
                result += self.evaluate(stmt)
        result += "End If"
        return result

    def kw_loop(self, node: Loop):
        result = "Do"
        if node.top_check:
            result += " While " + self.evaluate(node.guard)
        for stmt in node.block:
            self.evaluate(stmt)
        result += "Loop"
        if not node.top_check:
            result += " While " + self.evaluate(node.guard)
        return result

    def kw_print(self, node: Print):
        if not node.args:
            return "Print"
        result = "Print "
        for arg in node.args:
            if arg == Print.Element.COMMA:
                result += ", "
            elif arg == Print.Element.SEMICOLON:
                result += "; "
            elif arg == Print.Element.USING:
                result += " Using "
            else:
                result += self.evaluate(arg)
        return result.rstrip(" ")

    def proc_declaration(self, node: ProcDeclaration):
        result = "Declare "
        result += "Sub " if node.signature.ret == TYPE__NONE else "Function "
        result += node.name
        if node.signature.params:
            result += (
                "("
                + ", ".join(
                    [
                        param.source_name
                        for param in node.signature.params
                        if param.source_name
                    ]
                )
                + ")"
            )
        return result

    def proc_definition_location(self, node: ProcDefinitionLocation):
        proc = node.proc
        is_sub = proc.signature.ret == TYPE__NONE
        result = "Sub " if is_sub else "Function "
        result += proc.name
        if proc.signature.params:
            result += (
                "("
                + ", ".join(
                    [
                        param.source_name
                        for param in proc.signature.params
                        if param.source_name
                    ]
                )
                + ")"
            )
        for stmt in proc.statements:
            result += self.evaluate(stmt)
        result += "End "
        result += "Sub" if is_sub else "Function"
        return result

    def set_return(self, node: SetReturn):
        return node.impl.name + " = " + self.evaluate(node.value)

    def var(self, node: Var):
        if node.parens:
            return "(" + node.target.source_name + ")"
        return node.target.source_name


def format_ast(program: Program):
    return FormatPass(program).start()


class FormatContext:
    def __init__(self, program: Program, caps_style: Capitalisation):
        self.diags = DiagnosticStore()
        self.tok: LexToken = LexToken()
        self.symbols = program.symbols
        self.token_stream = Lexer(self.symbols, self.diags)
        self.caps_style = caps_style
        self.result = ""
        self.at_statment_position = True
        self.at_flex_space = False
        self.at_force_stick = False
        self.ast_walker = _ast_walk(program.main, 0, program.main)
        self.node = next(self.ast_walker)
        self.main = program.main
        self.token_stream.input(program.input)
        next(self)

    def __next__(self):
        try:
            self.tok = next(self.token_stream)
        except StopIteration:
            eof = LexToken()
            eof.lexer = self.tok.lexer
            eof.lexend = eof.lexpos = self.tok.lexer.lexlen
            eof.type = "EOF"
            eof.value = "<end of file>"
            self.tok = eof
        try:
            self.node = self.ast_walker.send(self.tok.lexpos)
        except StopIteration:
            self.node = self.main
        return self.tok

    def at_a(self, type: str, value: str | None = None) -> bool:
        return self.tok.type == type and (value is None or self.tok.value == value)

    def at_line_terminator(self):
        """
        Is current token a newline/:, else or EOF?
        """
        return self.at_a("NEWLINE") or self.at_a("KEYWORD", "else") or self.at_a("EOF")

    def case(self, camel: str, actual: str):
        if self.caps_style == Capitalisation.UPPER:
            return camel.upper()
        if self.caps_style == Capitalisation.CAMEL:
            return camel
        return actual

    def add(self, text: str):
        if self.at_flex_space and not self.at_force_stick:
            self.result += " "
        self.at_flex_space = False
        self.at_force_stick = False
        self.result += text
        self.at_statment_position = False

    def newline(self):
        self.result += "\n"
        self.at_statment_position = True
        self.at_flex_space = False

    def pre_flex(self):
        if not self.at_statment_position:
            self.at_flex_space = True

    def post_flex(self):
        self.at_flex_space = True

    def no_flex(self):
        self.at_flex_space = False

    def force_stick(self):
        self.at_force_stick = True

    def statement_position(self):
        self.at_statment_position = True


def format(program: Program, caps_style: Capitalisation = Capitalisation.UPPER):
    ctx = FormatContext(program, caps_style)
    while not ctx.at_a("EOF"):
        match (ctx.tok.type, ctx.tok.value):
            case ("NEWLINE", "rem"):
                ctx.pre_flex()
                ctx.add(
                    ctx.case("Rem", ctx.tok.plain_value[:3]) + ctx.tok.plain_value[3:]
                )
            case ("NEWLINE", "'"):
                ctx.pre_flex()
                ctx.add(ctx.tok.plain_value)
            case ("NEWLINE", ":"):
                ctx.no_flex()
                ctx.add(":")
                ctx.post_flex()
                ctx.statement_position()
            case ("NEWLINE", "\n"):
                ctx.newline()
            case ("KEYWORD", keyword):
                assert isinstance(keyword, str)
                ctx.pre_flex()
                ctx.add(ctx.case(KEYWORDS[keyword], ctx.tok.plain_value))
                ctx.post_flex()
            case ("VARIABLE", var):
                assert isinstance(var, Variable)
                name, _ = _split_name_sigil(var.source_name)
                _, sigil = _split_name_sigil(ctx.tok.plain_value)
                ctx.add(name + sigil)
            case ("PROCEDURE", proc):
                assert isinstance(proc, Procedure)
                name, _ = _split_name_sigil(proc.source_name)
                used_name, sigil = _split_name_sigil(ctx.tok.plain_value)
                stmt = ctx.at_statment_position
                ctx.add(ctx.case(name, used_name) + sigil)
                if stmt:
                    ctx.post_flex()
            case ("TYPE", type):
                assert isinstance(type, Type)
                ctx.pre_flex()
                ctx.add(ctx.case(type.name, ctx.tok.plain_value))
                ctx.post_flex()
            case ("STRING_LIT", text):
                assert isinstance(text, str)
                ctx.add('"' + text + '"')
            case ("NUM_LIT", _):
                ctx.add(ctx.tok.plain_value.upper())
            case ("PUNCTUATION", "+"):
                if not (
                    isinstance(ctx.node, Call)
                    and ctx.node.impl
                    and len(ctx.node.impl.signature.params) == 1
                ):
                    ctx.pre_flex()
                    ctx.add("+")
                    ctx.post_flex()
            case ("PUNCTUATION", "-"):
                ctx.pre_flex()
                ctx.add("-")
                if (
                    isinstance(ctx.node, Call)
                    and ctx.node.impl
                    and len(ctx.node.impl.signature.params) == 1
                ):
                    ctx.force_stick()
                else:
                    ctx.post_flex()
            case ("PUNCTUATION", "(" | ")" as c):
                assert isinstance(c, str)
                ctx.add(c)
            case ("PUNCTUATION", ","):
                ctx.add(",")
                ctx.post_flex()
            case ("PUNCTUATION", c):
                assert isinstance(c, str)
                ctx.pre_flex()
                ctx.add(c)
                ctx.post_flex()
        with contextlib.suppress(DiagnosticError):
            next(ctx)
    return ctx.result


def _split_name_sigil(s: str):
    match = re.match(r"([a-z0-9_.]+)(.*)", s, re.IGNORECASE)
    assert match is not None
    return match.group(1, 2)


def _ast_walk(node: Node, target_pos: int, parent: Node) -> Generator[Node, int, int]:
    while True:
        if target_pos < node.lex_start:
            target_pos = yield parent
        elif node.lex_end <= target_pos:
            return target_pos
        else:
            for child in node.children():
                target_pos = yield from _ast_walk(child, target_pos, node)
            if target_pos < node.lex_end:
                target_pos = yield node
