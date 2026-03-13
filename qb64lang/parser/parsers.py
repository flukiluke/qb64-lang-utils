from collections.abc import Callable

from . import diagnostics as diag
from .ast import (
    Assignment,
    Call,
    CompoundDefinition,
    Constant,
    Dim,
    DimArrayItem,
    DimScalarItem,
    Expr,
    For,
    If,
    Loop,
    Print,
    ProcDeclaration,
    ProcDefinition,
    ProcDefinitionLocation,
    Procedure,
    SetReturn,
    Statement,
)
from .context import ParseContext
from .datatypes import (
    TYPE__BYTE,
    TYPE__NONE,
    TYPE_STRING,
    CompoundField,
    CompoundType,
    Parameter,
    Type,
    TypeSignature,
    validate_fixed_width,
)
from .expression import do_bare_var, do_expr, do_func_args, do_lvalue
from .lexer import Id, Number


def do_print(ctx: ParseContext):
    """
    Expects: PRINT or ?
    Format: PRINT|? (expr|,|;)* [USING expr ; (expr|,|;)+]
    """
    result = Print(lex_start=ctx.tok.lexpos, lex_end=ctx.tok.lexend)
    next(ctx)
    using = False
    while not ctx.at_line_terminator():
        if ctx.at_a("PUNCTUATION", ","):
            result.args.append(Print.Element.COMMA)
            next(ctx)
        elif ctx.at_a("PUNCTUATION", ";"):
            result.args.append(Print.Element.SEMICOLON)
            next(ctx)
        elif ctx.at_a("KEYWORD", "using"):
            if using:
                ctx.diags.raise_error(diag.E_DUPE_USING, ctx.tok)
            result.args.append(Print.Element.USING)
            next(ctx)
            result.args.append(do_expr(ctx))
            ctx.consume("PUNCTUATION", ";")
            result.args.append(Print.Element.SEMICOLON)
            if ctx.at_line_terminator():
                ctx.diags.raise_error(
                    diag.E_UNEXPECTED_ITEM, ctx.tok, ctx.tok.value, "an expression"
                )
            using = True
        else:
            # If two expressions would be adjacent, insert a semicolon between
            if result.args and result.args[-1] not in (
                Print.Element.COMMA,
                Print.Element.SEMICOLON,
            ):
                result.args.append(Print.Element.SEMICOLON)
            result.args.append(do_expr(ctx))
    result.lex_end = ctx.prev.lexend
    return result


def do_if(ctx: ParseContext):
    """
    Expects: IF
    """

    def single_line_block(then_section: bool) -> list[Statement]:
        stmts: list[Statement] = []
        ctx.skip("NEWLINE", ":")
        with ctx.nestings.nest(node):
            while not (
                ctx.at_a("NEWLINE", "\n")
                or ctx.at_a("EOF")
                or (then_section and ctx.at_a("KEYWORD", "else"))
            ):
                stmt = do_stmt(ctx)
                if stmt:
                    stmts.append(stmt)
                ctx.skip("NEWLINE", ":")
        return stmts

    lex_start = ctx.tok.lexpos
    next(ctx)
    guard = do_expr(ctx)
    ctx.consume("KEYWORD", "then")
    # A REM after THEN acts as a command; we remain in single-line if mode
    if ctx.at_a("NEWLINE", "rem"):
        # Do not advance token so we leave it at a NEWLINE
        return If(
            guard,
            [],
            [],
            [],
            is_single_line=True,
            lex_start=lex_start,
            lex_end=ctx.prev.lexend,
        )

    node = If(guard, lex_start=lex_start, lex_end=ctx.tok.lexend)

    if not ctx.at_a("NEWLINE", "\n"):
        # Single-line IF
        node.true_branch = single_line_block(then_section=True)
        if ctx.at_a("KEYWORD", "else"):
            next(ctx)
            node.false_branch = single_line_block(then_section=False)
        node.is_single_line = True
    else:
        with ctx.nestings.nest(node):
            node.true_branch = do_block(ctx)
        while ctx.at_a("KEYWORD", "elseif"):
            next(ctx)
            elseif_guard = do_expr(ctx)
            ctx.consume("KEYWORD", "then")
            with ctx.nestings.nest(node):
                elseif_thens = do_block(ctx)
            node.elseifs.append((elseif_guard, elseif_thens))
        if ctx.at_a("KEYWORD", "else"):
            next(ctx)
            with ctx.nestings.nest(node):
                node.false_branch = do_block(ctx)
        if ctx.at_a("KEYWORD", "endif"):
            next(ctx)
        elif ctx.at_a("KEYWORD", "end"):
            next(ctx)
            ctx.consume("KEYWORD", "if")
        else:
            ctx.diags.raise_error(
                diag.E_UNEXPECTED_ITEM, ctx.tok, ctx.tok.value, "end if"
            )
    node.lex_end = ctx.prev.lexend
    return node


def do_do(ctx: ParseContext):
    """
    Expects: DO
    """

    def loop_guard() -> Expr | None:
        if ctx.at_a("KEYWORD", "while"):
            next(ctx)
            return do_expr(ctx)
        elif ctx.at_a("KEYWORD", "until"):
            next(ctx)
            return Call(
                ctx.symbols.procedures["<>"],
                [
                    do_expr(ctx),
                    Constant(
                        0,
                        TYPE__BYTE,
                        lex_start=ctx.prev.lexend,
                        lex_end=ctx.prev.lexend,
                    ),
                ],
                style=Call.Style.INFIX,
                lex_start=ctx.prev.lexend,
                lex_end=ctx.prev.lexend,
            )
        elif ctx.at_line_terminator():
            return None
        else:
            ctx.diags.raise_error(
                diag.E_UNEXPECTED_ITEM,
                ctx.tok,
                ctx.tok.value,
                "while or until or <newline>",
            )

    node = Loop(None, [], None, lex_start=ctx.tok.lexpos, lex_end=ctx.tok.lexend)
    next(ctx)
    node.top_guard = loop_guard()
    ctx.consume("NEWLINE")
    with ctx.nestings.nest(node):
        node.block = do_block(ctx)
    ctx.consume("KEYWORD", "loop")
    node.bottom_guard = loop_guard()
    node.lex_end = ctx.prev.lexend
    if node.top_guard and node.bottom_guard:
        ctx.diags.create(diag.E_TOO_MANY_LOOP_GUARDS, node)
    return node


def do_while(ctx: ParseContext):
    """
    Expects: WHILE
    """
    node = Loop(None, [], None, lex_start=ctx.tok.lexpos, lex_end=ctx.tok.lexend)
    next(ctx)
    node.top_guard = do_expr(ctx)
    ctx.consume("NEWLINE")
    with ctx.nestings.nest(node):
        node.block = do_block(ctx)
    ctx.consume("KEYWORD", "wend")
    node.lex_end = ctx.prev.lexend
    return node


def do_for(ctx: ParseContext):
    """
    Expects: FOR
    """
    lex_start = ctx.tok.lexpos
    next(ctx)
    var = do_bare_var(ctx)
    ctx.consume("PUNCTUATION", "=")
    start_value = do_expr(ctx)
    ctx.consume("KEYWORD", "to")
    end_value = do_expr(ctx)
    if ctx.at_a("KEYWORD", "step"):
        next(ctx)
        step_value = do_expr(ctx)
    elif ctx.at_a("NEWLINE"):
        step_value = Constant(
            1, var.target.type, lex_start=ctx.prev.lexend, lex_end=ctx.prev.lexend
        )
    else:
        ctx.diags.raise_error(
            diag.E_UNEXPECTED_ITEM, ctx.tok, ctx.tok.value, "step or <newline>"
        )
    ctx.consume("NEWLINE")
    node = For(
        var,
        start_value,
        end_value,
        step_value,
        [],
        lex_start=lex_start,
        lex_end=ctx.tok.lexend,
    )
    with ctx.nestings.nest(node):
        node.block = do_block(ctx)
    ctx.consume("KEYWORD", "next")
    if not ctx.at_line_terminator():
        next_var_tok = ctx.tok
        next_var = do_bare_var(ctx)
        if var.target != next_var.target:
            ctx.diags.raise_error(
                diag.E_FOR_NEXT_VAR_MISMATCH,
                next_var_tok,
                next_var.target.name,
                var.target.name,
            )
        if ctx.at_a("PUNCTUATION", ","):
            # Annoying NEXT k, j, i style. Insert newline + another NEXT token,
            # effectively expanding it to NEXT k : NEXT j, i
            ctx.prev.type = "NEWLINE"
            ctx.prev.value = ":"
            ctx.tok.type = "KEYWORD"
            ctx.tok.value = "next"
            ctx.reverse()

    node.lex_end = ctx.prev.lexend
    return node


def do_proc_ident(ctx: ParseContext) -> tuple[str, str, Type]:
    """
    Expects: SUB or FUNCTION
    Rresults: after name sigil
    """
    if ctx.at_a("KEYWORD", "sub"):
        is_sub = True
    elif ctx.at_a("KEYWORD", "function"):
        is_sub = False
    else:
        ctx.diags.raise_error(diag.E_UNEXPECTED_ITEM, ctx.tok, "SUB or FUNCTION")
    default_type = ctx.symbols.default_type
    try:
        if is_sub:
            ctx.symbols.default_type = TYPE__NONE
        ctx.symbols.return_proc_as_id = True
        next(ctx)
        if not ctx.at_a("ID"):
            ctx.diags.raise_error(diag.E_NAME_IN_USE, ctx.tok, ctx.tok.value)
    finally:
        ctx.symbols.default_type = default_type
        ctx.symbols.return_proc_as_id = False
    var_id: Id = ctx.tok.value
    cased_name: str = ctx.tok.plain_value
    if is_sub and var_id.sigil:
        ctx.diags.create(diag.E_SUB_WITH_TYPE, ctx.tok)
    next(ctx)
    return (var_id.name, cased_name, var_id.type)


def do_declare_prepass(ctx: ParseContext):
    """
    Expects: DECLARE
    """
    lex_start = ctx.tok.lexpos
    next(ctx)
    name, cased_name, ret = do_proc_ident(ctx)
    strictsigil = ctx.flags.syntax.get("strictsigil") is not None
    if strictsigil and ret == TYPE_STRING:
        name += "$"
    proc = ctx.symbols.find_procedure(name)
    if proc is None:
        proc = Procedure(name, cased_name, [], ctx.flags.builtin)
        ctx.symbols.add_procedure(proc)
    elif not ctx.flags.allow_proc_overloads:
        ctx.diags.raise_error(diag.E_OVERLOAD_PROHIBITED, ctx.prev, name)
    params = do_param_list(ctx)
    impl = ProcDefinition(
        name,
        TypeSignature(ret, params),
        decl_only=True,
        strictsigil=strictsigil,
        lex_start=lex_start,
        lex_end=ctx.prev.lexend,
    )
    proc.impls.append(impl)


def do_declare(ctx: ParseContext):
    """
    Expects: DECLARE
    """
    if ctx.nestings.items:
        ctx.diags.raise_error(diag.E_NOT_TOPLEVEL, ctx.tok, ctx.tok.plain_value)
    lex_start = ctx.tok.lexpos
    next(ctx)
    name, _, ret = do_proc_ident(ctx)
    strictsigil = ctx.flags.syntax.get("strictsigil") is not None
    if strictsigil and ret == TYPE_STRING:
        name += "$"
    proc = ctx.symbols.find_procedure(name)
    if proc is None:
        # All valid procs exist from the prepass, so this one had some kind of error.
        ctx.diags.raise_error(diag.E_UNFOUND_PROC, ctx.tok)
    params = do_param_list(ctx)
    impl = proc.find_impl(TypeSignature(ret, params))
    if impl is None:
        # All valid impls exist from the prepass, so this one had some kind of error.
        ctx.diags.raise_error(diag.E_UNFOUND_PROC, ctx.tok)
    return ProcDeclaration(
        name, impl.signature, lex_start=lex_start, lex_end=ctx.prev.lexend
    )


def do_array_bounds(ctx: ParseContext) -> list[Expr | tuple[Expr, Expr]]:
    bounds = list[Expr | tuple[Expr, Expr]]()
    ctx.consume("PUNCTUATION", "(")
    while True:
        bound = do_expr(ctx)
        if ctx.at_a("KEYWORD", "to"):
            lbound = bound
            next(ctx)
            ubound = do_expr(ctx)
            bounds.append((lbound, ubound))
        else:
            bounds.append(bound)
        if ctx.at_a("PUNCTUATION", ","):
            next(ctx)
        else:
            break
    ctx.consume("PUNCTUATION", ")")
    return bounds


def do_dim(ctx: ParseContext):
    """
    Expects: DIM or REDIM
    """

    def dim_item():
        var_tok = ctx.tok
        tok_val: Id = var_tok.value
        next(ctx)
        bounds = None
        if ctx.at_a("PUNCTUATION", "("):
            bounds = do_array_bounds(ctx)
        trailing_type = do_as_type_clause(ctx)
        if tok_val.sigil and (leading_type or trailing_type):
            ctx.diags.raise_error(diag.E_SIGIL_WITH_AS, var_tok)
        elif leading_type and trailing_type:
            ctx.diags.raise_error(diag.E_DUPE_AS_TYPE, var_tok)
        type = leading_type or trailing_type or tok_val.type
        if bounds:
            type = ctx.symbols.lookup_array_type(type, len(bounds))
        var = ctx.symbols.create_local(tok_val.name, var_tok.plain_value, type)
        if bounds:
            return DimArrayItem(
                var, bounds, lex_start=var_tok.lexpos, lex_end=ctx.prev.lexend
            )
        else:
            return DimScalarItem(var, lex_start=var_tok.lexpos, lex_end=ctx.prev.lexend)

    lex_start = ctx.tok.lexpos
    items = list[DimScalarItem | DimArrayItem]()
    is_redim = ctx.at_a("KEYWORD", "redim")
    next(ctx)
    leading_type = do_as_type_clause(ctx)
    while ctx.at_a("ID"):
        items.append(dim_item())
        if ctx.at_a("PUNCTUATION", ","):
            next(ctx)
        else:
            break
    return Dim(
        items, is_redim, leading_type, lex_start=lex_start, lex_end=ctx.prev.lexend
    )


def do_type(ctx: ParseContext):
    lex_start = ctx.tok.lexpos
    next(ctx)
    if not ctx.at_a("TYPE") or ctx.tok.value.is_builtin():
        ctx.diags.raise_error(diag.E_UNFOUND_PROC, ctx.tok)
    type: CompoundType = ctx.tok.value
    while not ctx.at_a("KEYWORD", "end"):
        next(ctx)
    ctx.consume("KEYWORD", "end")
    ctx.consume("KEYWORD", "type")
    node = CompoundDefinition(type, lex_start=lex_start, lex_end=ctx.prev.lexend)
    if len(type.fields) == 0:
        ctx.diags.create(diag.E_EMPTY_COMPOUND, node)
    return node


def do_type_prepass(ctx: ParseContext):
    """
    Expects: TYPE
    """
    fields = list[CompoundField]()
    field_names = set[str]()

    def bare_list(as_clause: Type) -> list[CompoundField]:
        result = list[CompoundField]()
        while ctx.at_a("ID"):
            var_id: Id = ctx.tok.value
            if var_id.sigil is not None:
                ctx.diags.raise_error(diag.E_SIGIL_WITH_FIELD_NAME, ctx.tok)
            if var_id.name in field_names:
                ctx.diags.create(
                    diag.E_DUPE_COMPOUND_FIELD, ctx.tok, ctx.tok.plain_value
                )
            elif "." in var_id.name:
                ctx.diags.create(diag.E_DOT_PROHIBITED, ctx.tok, ctx.tok.plain_value)
            else:
                result.append(
                    CompoundField(as_clause, var_id.name, ctx.tok.plain_value)
                )
                field_names.add(var_id.name)
            next(ctx)
            if ctx.at_a("PUNCTUATION", ","):
                next(ctx)
            else:
                break
        return result

    def typed_item() -> list[CompoundField]:
        if not ctx.at_a("ID"):
            ctx.diags.raise_error(diag.E_NAME_IN_USE, ctx.tok, ctx.tok.value)
        var_id = ctx.tok.value
        if var_id.sigil is not None:
            ctx.diags.raise_error(diag.E_SIGIL_WITH_FIELD_NAME, ctx.tok)
        name_tok = ctx.tok
        cased_name: str = ctx.tok.plain_value
        next(ctx)
        as_clause = do_as_type_clause(ctx)
        if as_clause is None:
            ctx.diags.raise_error(diag.E_MISSING_AS_TYPE, ctx.tok)
        if var_id.name in field_names:
            ctx.diags.create(diag.E_DUPE_COMPOUND_FIELD, name_tok, name_tok.plain_value)
            return []
        elif "." in var_id.name:
            ctx.diags.create(diag.E_DOT_PROHIBITED, ctx.tok, ctx.tok.plain_value)
            return []
        else:
            field_names.add(var_id.name)
            return [CompoundField(as_clause, var_id.name, cased_name)]

    try:
        ctx.symbols.return_proc_as_id = True
        ctx.symbols.return_var_as_id = True
        next(ctx)
        if not ctx.at_a("ID"):
            ctx.diags.raise_error(diag.E_NAME_IN_USE, ctx.tok, ctx.tok.value)
        var_id: Id = ctx.tok.value
        cased_name: str = ctx.tok.plain_value
        if var_id.sigil is not None:
            ctx.diags.raise_error(diag.E_SIGIL_WITH_TYPE_NAME, ctx.tok)
        if "." in var_id.name:
            ctx.diags.raise_error(diag.E_DOT_PROHIBITED, ctx.tok, ctx.tok.plain_value)
        next(ctx)
        ctx.consume("NEWLINE")
        while not ctx.at_a("KEYWORD", "end"):
            as_clause = do_as_type_clause(ctx)
            fields.extend(bare_list(as_clause) if as_clause else typed_item())
            ctx.consume("NEWLINE")
        ctx.consume("KEYWORD", "end")
        ctx.consume("KEYWORD", "type")
    finally:
        ctx.symbols.return_proc_as_id = False
        ctx.symbols.return_var_as_id = False
    ctx.symbols.create_compound_type(var_id.name, cased_name, fields)


KEYWORD_PARSERS: dict[str, Callable[[ParseContext], Statement]] = {
    "print": do_print,
    "?": do_print,
    "if": do_if,
    "do": do_do,
    "while": do_while,
    "for": do_for,
    "declare": do_declare,
    "dim": do_dim,
    "redim": do_dim,
    "type": do_type,
}


def is_eob(ctx: ParseContext):
    match ctx.tok.type, ctx.tok.value:
        case "EOF", _:
            return True
        case "KEYWORD", (
            "else"
            | "elseif"
            | "endif"
            | "loop"
            | "next"
            | "wend"
            | "case"
            | "sub"
            | "function"
        ):
            return True
        case "KEYWORD", "end":
            next(ctx)
            result = not ctx.at_line_terminator()
            ctx.reverse()
            return result
        case _:
            return False


def name_close_match(ctx: ParseContext):
    """
    Assuming ctx is at a closing KEYWORD, give the name of the opening
    KEYWORD it is paired with.
    """
    match ctx.tok.value:
        case "else" | "elseif" | "endif":
            return "if"
        case "loop":
            return "do"
        case "next":
            return "for"
        case "wend":
            return "while"
        case "case":
            return "select"
        case "end":
            next(ctx)
            name = ctx.tok.value
            ctx.reverse()
            return name
        case _:
            return "opening keyword"


def do_prepass(ctx: ParseContext):
    def do_prepass_line():
        ctx.skip("NEWLINE")
        match (ctx.tok.type, ctx.tok.value):
            case ("KEYWORD", "declare"):
                do_declare_prepass(ctx)
            case ("KEYWORD", "sub" | "function"):
                do_sub_function_prepass(ctx)
            case ("KEYWORD", "type"):
                do_type_prepass(ctx)
            case _:
                ctx.drop_line()

    try:
        next(ctx)
    except diag.DiagnosticError:
        ctx.drop_line()
    while not ctx.at_a("EOF"):
        try:
            do_prepass_line()
        except diag.DiagnosticError:
            ctx.drop_line()


def do_main(ctx: ParseContext):
    if main_proc := ctx.symbols.find_procedure("_main"):
        main = main_proc.impls[0]
    else:
        main = ProcDefinition(
            "_main",
            TypeSignature(TYPE__NONE, []),
            ctx.symbols.scope,
            lex_start=0,
            lex_end=0,
        )
        ctx.symbols.add_procedure(Procedure("_main", "_Main", [main]))
    try:
        next(ctx)
    except diag.DiagnosticError:
        ctx.drop_line()
    while not ctx.at_a("EOF"):
        ctx.symbols.set_scope(main.symbols)
        main.statements.extend(do_block(ctx))
        if ctx.at_a("KEYWORD", "sub") or ctx.at_a("KEYWORD", "function"):
            try:
                main.statements.append(do_sub_function(ctx))
            except diag.DiagnosticError:
                ctx.drop_line()
        elif ctx.at_a("EOF"):
            break
        elif is_eob(ctx):
            ctx.diags.create(
                diag.E_CLOSE_KEYWORD_NO_OPEN,
                ctx.tok,
                ctx.tok.value,
                name_close_match(ctx),
            )
            ctx.drop_line()
    ctx.symbols.set_scope(main.symbols)
    main.lex_end = ctx.prev.lexend
    return main


def do_sub_function_prepass(ctx: ParseContext):
    lex_start = ctx.tok.lexpos
    # Grab this token for error reporting purposes
    start_tok = ctx.tok
    name, cased_name, ret = do_proc_ident(ctx)

    # Procedure may exist if pre-declared, or other impls exist
    proc = ctx.symbols.find_procedure(name)
    if proc is None:
        proc = Procedure(name, cased_name, [], ctx.flags.builtin)
        ctx.symbols.add_procedure(proc)
    params = do_param_list(ctx)
    sig = TypeSignature(ret, params)

    impl = proc.find_impl(sig)
    if not impl and len(proc.impls) and not ctx.flags.allow_proc_overloads:
        ctx.diags.raise_error(diag.E_OVERLOAD_PROHIBITED, start_tok, name)
    elif not impl:
        impl = ProcDefinition(name, sig, lex_start=lex_start, lex_end=ctx.prev.lexend)
        proc.impls.append(impl)
    elif impl.decl_only:
        impl.decl_only = False
    else:
        ctx.diags.raise_error(diag.E_NAME_IN_USE, start_tok, name)


def do_sub_function(ctx: ParseContext) -> ProcDefinitionLocation:
    if ctx.nestings.items:
        ctx.diags.raise_error(diag.E_NOT_TOPLEVEL, ctx.tok, ctx.tok.plain_value)
    lex_start = ctx.tok.lexpos
    name, _, ret = do_proc_ident(ctx)
    proc = ctx.symbols.find_procedure(name)
    if proc is None:
        # All valid procs exist from the prepass, so this one had some kind of error.
        ctx.diags.raise_error(diag.E_UNFOUND_PROC, ctx.tok)
    params = do_param_list(ctx)
    impl = proc.find_impl(TypeSignature(ret, params))
    if impl is None:
        # All valid impls exist from the prepass, so this one had some kind of error.
        ctx.diags.raise_error(diag.E_UNFOUND_PROC, ctx.tok)
    ctx.symbols.set_scope(impl.symbols)
    for param in params:
        assert param.name is not None
        assert param.source_name is not None
        ctx.symbols.create_local(param.name, param.source_name, param.type)
    with ctx.nestings.nest(impl):
        ctx.consume("NEWLINE")
        impl.statements = do_block(ctx)

        ctx.consume("KEYWORD", "end")
        if ctx.at_a("KEYWORD", "sub"):
            ctx.consume("KEYWORD", "sub")
        else:
            ctx.consume("KEYWORD", "function")
        impl.lex_start = lex_start
        impl.lex_end = ctx.prev.lexend
        return ProcDefinitionLocation(
            impl, lex_start=lex_start, lex_end=ctx.prev.lexend
        )


def do_as_type_clause(ctx: ParseContext):
    """
    Expects: AS or other
    Return a type if AS T clause if present, otherwise None
    """
    if not ctx.at_a("KEYWORD", "as"):
        return None
    next(ctx)
    unsigned = False
    if ctx.at_a("KEYWORD", "_unsigned"):
        unsigned = True
        next(ctx)
    base_tok = ctx.tok
    if not ctx.at_a("TYPE"):
        ctx.diags.raise_error(diag.E_NOT_A_TYPE, base_tok)
    base_type: Type = ctx.tok.value
    next(ctx)
    width = None
    if ctx.at_a("PUNCTUATION", "*"):
        next(ctx)
        if not ctx.at_a("NUM_LIT") or ctx.tok.value.style != Number.Style.INT:
            ctx.diags.raise_error(
                diag.E_UNEXPECTED_ITEM, ctx.tok, ctx.tok.value, "an integer number"
            )
        width = ctx.tok.value.value
        next(ctx)
    if unsigned:
        type = ctx.symbols.find_type("_unsigned " + base_type.name)
        if type is None:
            ctx.diags.raise_error(diag.E_NOT_A_TYPE, base_tok)
    else:
        type = base_type
    if width is not None:
        validate_fixed_width(type, width, base_tok, ctx.diags)
        type = ctx.symbols.lookup_sigil(type.sigil + str(width))
    return type


def do_param_list(ctx: ParseContext):
    """
    Expects: (
    Results: after )
    """
    result = list[Parameter]()
    if not ctx.at_a("PUNCTUATION", "("):
        return result
    ctx.consume("PUNCTUATION", "(")
    while True:
        if not ctx.at_a("ID"):
            ctx.diags.raise_error(diag.E_NAME_IN_USE, ctx.tok, ctx.tok.value)
        var_tok = ctx.tok
        var_id: Id = var_tok.value
        type = var_id.type
        next(ctx)
        trailing_type = do_as_type_clause(ctx)
        if trailing_type and var_id.sigil:
            ctx.diags.raise_error(diag.E_SIGIL_WITH_AS, var_tok)
        elif trailing_type:
            type = trailing_type
        result.append(Parameter(type, var_id.name, var_tok.plain_value))
        if ctx.at_a("PUNCTUATION", ")"):
            break
        ctx.consume("PUNCTUATION", ",")
    ctx.consume("PUNCTUATION", ")")
    return result


def do_block(ctx: ParseContext) -> list[Statement]:
    """
    Expects: start of statement
    Results: End of block marker
    Note: The end of block marker is:
        - END for END <x> keywords (x=IF, SELECT, SUB, FUNCTION),
        - the keyword itself for ELSE, ELSEIF, ENDIF, LOOP, NEXT, WEND, CASE
        - The SUB or FUNCTION keywords (indicating a change of scope)
        - EOF
    """

    block: list[Statement] = []
    ctx.skip("NEWLINE")
    if ctx.nestings.items and (
        ctx.at_a("KEYWORD", "sub") or ctx.at_a("KEYWORD", "function")
    ):
        ctx.diags.create(diag.E_NOT_TOPLEVEL, ctx.tok, ctx.tok.plain_value)
        ctx.drop_line()
    while not is_eob(ctx):
        try:
            stmt = do_stmt(ctx)
        except diag.DiagnosticError:
            stmt = None
            ctx.drop_line()
        if stmt:
            block.append(stmt)
        ctx.skip("NEWLINE")
    return block


def do_stmt(ctx: ParseContext) -> Statement | None:
    result = None
    ctx.skip("NEWLINE")
    match ctx.tok.type:
        case "KEYWORD":
            handler = KEYWORD_PARSERS.get(ctx.tok.value)
            if handler is None:
                ctx.diags.raise_error(diag.E_UNEXPECTED_KEYWORD, ctx.tok, ctx.tok.value)
            result = handler(ctx)
        case "VARIABLE":
            # Asignment to existing variable
            result = do_assignment(ctx)
        case "PROCEDURE":
            if (
                ctx.nestings.items
                and isinstance(ctx.nestings.items[0], ProcDefinition)
                and ctx.nestings.items[0].name == ctx.tok.value.name
                and ctx.nestings.items[0].signature.ret != TYPE__NONE
            ):
                result = do_set_return(ctx)
            else:
                # Call to existing procedure
                result = do_procedure_call(ctx)
        case "ID":
            # Assignment to an implicitly declared variable
            result = do_assignment(ctx)
        case _:
            ctx.diags.raise_error(
                diag.E_UNEXPECTED_ITEM, ctx.tok, ctx.tok.value, "a statement"
            )
    if not ctx.at_line_terminator():
        ctx.diags.raise_error(
            diag.E_UNEXPECTED_ITEM, ctx.tok, ctx.tok.value, "end of statement"
        )
    return result


def do_assignment(ctx: ParseContext):
    """
    Expects: first token of lvalue
    """
    lex_start = ctx.tok.lexpos
    lval = do_lvalue(ctx)
    ctx.consume("PUNCTUATION", "=")
    rval = do_expr(ctx)
    return Assignment(lval, rval, lex_start=lex_start, lex_end=ctx.prev.lexend)


def do_set_return(ctx: ParseContext):
    """
    Expects: function name in lvalue position
    """
    lex_start = ctx.tok.lexpos
    next(ctx)
    ctx.consume("PUNCTUATION", "=")
    impl = ctx.nestings.items[0]
    assert isinstance(impl, ProcDefinition)
    return SetReturn(impl, do_expr(ctx), lex_start=lex_start, lex_end=ctx.prev.lexend)


def do_procedure_call(ctx: ParseContext):
    """
    Expects: procedure name
    """
    target = ctx.tok.value
    lex_start = ctx.tok.lexpos
    next(ctx)
    if not ctx.at_line_terminator():
        args = do_func_args(ctx)
        return Call(
            target,
            args,
            style=Call.Style.STATEMENT,
            lex_start=lex_start,
            lex_end=ctx.prev.lexend,
        )
    return Call(
        target, style=Call.Style.STATEMENT, lex_start=lex_start, lex_end=ctx.prev.lexend
    )
