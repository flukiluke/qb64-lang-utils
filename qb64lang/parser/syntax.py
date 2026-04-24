import re
from dataclasses import dataclass, field

from qb64lang.parser.ast import Constant, Expr
from qb64lang.parser.datatypes import TYPE_INTEGER

from . import diagnostics as diag
from .context import ParseContext
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


@dataclass(eq=False)
class State:
    tag: str | None
    out: "State | None"

    def set_out(self, to: "State"):
        if self.out is None:
            self.out = to

    def accepts(self, tok: LexToken) -> Expr | None:
        return None

    def display(self) -> str:
        return "<unknown>"


@dataclass(eq=False)
class ExprState(State):
    pass

    def display(self):
        return "an expression"


@dataclass(eq=False)
class LiteralState(State):
    literal: str

    def accepts(self, tok: LexToken):
        if tok.plain_value.lower() == self.literal.lower():
            return Constant(-1, TYPE_INTEGER, lex_start=tok.lexpos, lex_end=tok.lexend)

    def display(self):
        return self.literal


@dataclass(eq=False)
class AlternationState(State):
    alts: list[None | State]

    def set_out(self, to):
        for i, alt in enumerate(self.alts):
            if alt is None:
                self.alts[i] = to
            else:
                alt.set_out(to)

    def display(self):
        return " or ".join([alt.display() for alt in self.alts if alt])


@dataclass(eq=False)
class MatchState(State):
    def display(self):
        return "<end of parameters>"


MATCH_STATE = MatchState(None, None)
MATCH_STATE.out = MATCH_STATE


@dataclass
class SyntaxSpec:
    start: State
    last_states: list[State]
    value_items: set[str]

    def join(self, other: "SyntaxSpec"):
        for state in self.last_states:
            state.set_out(other.start)
        self.last_states = other.last_states
        self.value_items.update(other.value_items)
        return self

    def eval(self, ctx: ParseContext):
        return eval_syntax_spec(self, ctx)


def build(lexer: Lexer, terminators: list[str] = []) -> SyntaxSpec:
    fragment: SyntaxSpec | None = None
    tag = None
    for tok in lexer:
        if tok.type in terminators:
            if fragment is None:
                raise SpecError("Empty fragment")
            return fragment
        match tok.type:
            case "LITERAL" | "PUNCTUATION":
                state = LiteralState(tag, None, tok.value)
                new_fragment = SyntaxSpec(state, [state], set([tag] if tag else []))
                tag = None
                if fragment:
                    fragment.join(new_fragment)
                else:
                    fragment = new_fragment
            case "EXPR":
                state = ExprState(tok.value, None)
                new_fragment = SyntaxSpec(state, [state], set([tok.value]))
                tag = None
                if fragment:
                    fragment.join(new_fragment)
                else:
                    fragment = new_fragment
            case "OBRACKET":
                option = build(lexer, ["CBRACKET"])
                state = AlternationState(tag, None, [None, option.start])
                value_items = set(option.value_items)
                if tag:
                    value_items.add(tag)
                new_fragment = SyntaxSpec(
                    state, option.last_states + [state], value_items
                )
                tag = None
                if fragment:
                    fragment.join(new_fragment)
                else:
                    fragment = new_fragment
            case "OBRACE":
                choices = list[SyntaxSpec]()
                value_items = set[str]()
                while lexer.last_token.type != "CBRACE":
                    frag = build(lexer, ["CBRACE", "PIPE"])
                    value_items.update(frag.value_items)
                    choices.append(frag)
                if tag:
                    value_items.add(tag)
                state = AlternationState(
                    tag, None, [choice.start for choice in choices]
                )
                new_fragment = SyntaxSpec(
                    state,
                    [s for choice in choices for s in choice.last_states],
                    value_items,
                )
                tag = None
                if fragment:
                    fragment.join(new_fragment)
                else:
                    fragment = new_fragment
            case "TAG":
                tag = tok.value
            case _:
                raise SpecError("Unexpected " + tok.value)
    if terminators:
        raise SpecError("Ended too soon")
    if fragment is None:
        raise SpecError("Empty fragment")
    return fragment


def _Lexer():
    t_ignore = " \t"
    t_OBRACKET = r"\["
    t_CBRACKET = r"\]"
    t_OBRACE = "{"
    t_CBRACE = "}"
    t_PIPE = r"\|"
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
        return build(lexer).join(SyntaxSpec(MATCH_STATE, [], set()))
    except SpecError as e:
        diags.raise_error(diag.E_BAD_SYNTAX_SPEC, start_tok, e.args[0])


TagMap = dict[str, Expr]


@dataclass(eq=False)
class SystemState:
    state: State
    parent_tags: TagMap
    alt_tag: tuple[str, int] | None = None

    def clone(self):
        return SystemState(self.state, dict(self.parent_tags), self.alt_tag)


@dataclass
class StateSet:
    literal: set[SystemState] = field(default_factory=set)
    expr: set[SystemState] = field(default_factory=set)
    match: set[SystemState] = field(default_factory=set)

    def transition(self):
        new_set = StateSet(self.literal, self.expr, self.match)
        self.literal = set()
        self.expr = set()
        self.match = set()
        return new_set

    def __len__(self):
        return len(self.literal) + len(self.expr) + len(self.match)


def eval_syntax_spec(spec: SyntaxSpec, ctx: ParseContext):
    cur_set = StateSet()
    next_set = StateSet()

    def add_state(
        new_state: State | None,
        accepted_sys_state: SystemState,
        tok: LexToken,
        value: Expr | None = None,
    ):
        assert new_state is not None

        tags = dict(accepted_sys_state.parent_tags)
        if accepted_sys_state.alt_tag:
            tags[accepted_sys_state.alt_tag[0]] = Constant(
                accepted_sys_state.alt_tag[1],
                TYPE_INTEGER,
                lex_start=tok.lexpos,
                lex_end=tok.lexend,
            )
        if accepted_sys_state.state.tag and value:
            tags[accepted_sys_state.state.tag] = value

        if isinstance(new_state, AlternationState):
            for i, alt in enumerate(new_state.alts, start=1):
                assert alt is not None
                alt_tag = (new_state.tag, i) if new_state.tag else None
                add_state(alt, SystemState(alt, tags, alt_tag), tok)
        elif isinstance(new_state, LiteralState):
            next_set.literal.add(SystemState(new_state, tags))
        elif isinstance(new_state, ExprState):
            next_set.expr.add(SystemState(new_state, tags))
        elif isinstance(new_state, MatchState):
            next_set.match.add(SystemState(new_state, tags))
        else:
            assert False, "Unknown state"

    add_state(spec.start, SystemState(spec.start, {}), ctx.tok)
    while True:
        cur_set = next_set.transition()
        nonexpr_accepted = False
        advanced = False
        # Check for literals we can accept.
        for sys_state in cur_set.literal:
            if value := sys_state.state.accepts(ctx.tok):
                add_state(sys_state.state.out, sys_state, ctx.tok, value)
                nonexpr_accepted = True
        # Otherwise try accept an expr.
        if not nonexpr_accepted and cur_set.expr and is_expr_start(ctx.tok):
            expr = do_expr(ctx)
            advanced = True
            for sys_state in cur_set.expr:
                add_state(sys_state.state.out, sys_state, ctx.tok, expr)
        # Be greedy: if we accepted anything, discard the assumption we were finished.
        if next_set:
            cur_set.match.clear()
        # Otherwise we accepted nothing, time to finish. Prefer the match state with
        # more tags.
        elif cur_set.match:
            match_tags = [m.parent_tags for m in cur_set.match]
            match_tags.sort(key=len)
            return match_tags.pop()
        else:
            # No new states and no current match states, this is an input error.
            expected = " or ".join(
                set(
                    [sys_state.state.display() for sys_state in cur_set.literal]
                    + ["an expression"]
                    if cur_set.expr
                    else [] + ["end of parameters"]
                    if cur_set.match
                    else []
                )
            )
            ctx.diags.raise_error(
                diag.E_UNEXPECTED_ITEM, ctx.prev, ctx.prev.plain_value, expected
            )
        # do_expr consumes the token but the literals don't, normalise the situation.
        if not advanced:
            next(ctx)
