import re
from dataclasses import dataclass, field

from . import diagnostics as diag
from .ast import Constant, Expr
from .context import ParseContext
from .datatypes import TYPE_INTEGER
from .expression import do_expr, is_expr_start
from .ply import Lexer, LexToken, Token, lex

# pyright: reportUnusedFunction=false, reportUnusedVariable=false
# ruff: noqa: F841

tokens = (
    "OBRACKET",
    "CBRACKET",
    "OBRACE",
    "CBRACE",
    "PIPE",
    "LITERAL",
    "PUNCTUATION",
    "EXPR",
    "TAG",
)


class SpecError(Exception):
    pass


@dataclass
class ExprItem:
    tag: str

    def accept(self, ctx: ParseContext) -> dict[str, Expr]:
        if is_expr_start(ctx.tok):
            return {self.tag: do_expr(ctx)}
        return {}

    def display(self):
        return "an expression"


@dataclass
class LiteralItem:
    literal: str
    tag: str | None = None

    def accept(self, ctx: ParseContext) -> dict[str, Expr]:
        # Use plain_value to ensure no sigils are present
        if self.literal.lower() == ctx.tok.plain_value.lower():
            next(ctx)
            return {
                self.tag if self.tag else "": Constant(
                    -1, TYPE_INTEGER, lex_start=ctx.prev.lexpos, lex_end=ctx.prev.lexend
                )
            }
        return {}

    def display(self):
        return self.literal


@dataclass
class OptionalItem:
    subspec: "SyntaxSpec"
    tag: str | None = None

    def accept(self, ctx: ParseContext) -> dict[str, Expr]:
        results = self.subspec.accept(ctx, allow_missing_start=True)
        if self.tag and "" in results:
            results[self.tag] = results[""]
        return results

    def display(self):
        return self.subspec.display()

    @staticmethod
    def build(lexer: Lexer):
        return OptionalItem(SyntaxSpec.build(lexer, "CBRACKET"))


@dataclass
class AlternateItem:
    alternates: list[str]
    tag: str | None = None

    def accept(self, ctx: ParseContext) -> dict[str, Expr]:
        tok_value = ctx.tok.plain_value.lower()
        for i, alternate in enumerate(self.alternates):
            if alternate.lower() == tok_value:
                next(ctx)
                return {
                    self.tag if self.tag else "": Constant(
                        i + 1,
                        TYPE_INTEGER,
                        lex_start=ctx.prev.lexpos,
                        lex_end=ctx.prev.lexend,
                    )
                }
        return {}

    def display(self):
        return " or ".join(self.alternates)

    @staticmethod
    def build(lexer: Lexer, tag: str | None):
        self = AlternateItem([], tag)
        for tok in lexer:
            if tok.type == "EXPR":
                self.alternates.append(tok.value)
            elif tok.type == "CBRACE":
                return self
            else:
                raise SpecError("Alternation requires plain words")
        raise SpecError("Missing end }")


@dataclass
class SyntaxSpec:
    items: list[ExprItem | LiteralItem | OptionalItem | AlternateItem] = field(
        default_factory=list
    )
    value_items: list[str] = field(default_factory=list)

    def accept(
        self, ctx: ParseContext, allow_missing_start: bool = False
    ) -> dict[str, Expr]:
        results = {}
        for item in self.items:
            if r := item.accept(ctx):
                results.update(r)
            elif allow_missing_start:
                return {}
            elif not isinstance(item, OptionalItem):
                ctx.diags.raise_error(
                    diag.E_UNEXPECTED_ITEM, ctx.tok, ctx.tok.plain_value, item.display()
                )
            allow_missing_start = False
        return results

    def display(self):
        return self.items[0].display()

    @staticmethod
    def build(lexer: Lexer, terminator: str | None = None):
        self = SyntaxSpec()
        tag = None
        for tok in lexer:
            if tok.type == terminator:
                return self
            match tok.type:
                case "OBRACKET":
                    item = OptionalItem.build(lexer)
                    self.items.append(item)
                    self.value_items.extend(item.subspec.value_items)
                    tag = None
                case "OBRACE":
                    if tag:
                        self.value_items.append(tag)
                    self.items.append(AlternateItem.build(lexer, tag))
                    tag = None
                case "LITERAL" | "PUNCTUATION":
                    if tag:
                        self.value_items.append(tag)
                    self.items.append(LiteralItem(tok.value, tag))
                    tag = None
                case "EXPR":
                    self.value_items.append(tok.value)
                    self.items.append(ExprItem(tok.value))
                    tag = None
                case "TAG":
                    tag = tok.value
                case _:
                    raise SpecError("Unexpected " + tok.value)
        if terminator:
            raise SpecError("Ended too soon")
        return self


def _Lexer():
    t_ignore = " \t"
    t_OBRACKET = r"\["
    t_CBRACKET = r"\]"
    t_OBRACE = "{"
    t_CBRACE = "}"
    t_PUNCTUATION = "[#,()-]"

    @Token("[a-z0-9_]+:")
    def t_TAG(t: LexToken):
        t.value = t.value.rstrip(":").lower()
        return t

    @Token('"(?P<literal>[^"]*)"')
    def t_LITERAL(t: LexToken):
        t.value = t.lexer.lexmatch.group("literal")
        return t

    @Token("[a-z0-9_]+")
    def t_EXPR(t: LexToken):
        t.value = t.value.lower()
        return t

    def t_error(t: LexToken):
        t.lexer.skip(len(t.value))
        t.lexend = t.lexpos + len(t.value)
        raise SpecError("Unexpected characters: " + t.value)

    return lex(reflags=re.VERBOSE | re.IGNORECASE)


def compile_syntax_spec(
    text: str, diags: diag.DiagnosticStore, start_tok: LexToken
) -> SyntaxSpec:
    lexer = _Lexer()
    lexer.input(text)
    try:
        return SyntaxSpec.build(lexer)
    except SpecError as e:
        diags.raise_error(diag.E_BAD_SYNTAX_SPEC, start_tok, e.args[0])
