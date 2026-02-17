"""Natural alias catalog for ICL source normalization."""

from __future__ import annotations

from dataclasses import dataclass


_ALIAS_MODES = {"core", "extended"}


@dataclass(frozen=True)
class AliasEntry:
    """Alias mapping for one canonical ICL token/identifier."""

    canonical: str
    aliases: tuple[str, ...]
    category: str
    tier: str
    description: str
    target_forms: dict[str, str]


_ALIAS_ENTRIES: tuple[AliasEntry, ...] = (
    AliasEntry(
        canonical="fn",
        aliases=("mkfn", "makefn", "defn", "func", "function"),
        category="statement",
        tier="core",
        description="Function definition keyword.",
        target_forms={
            "python": "def name(args): ...",
            "js": "function name(args) { ... }",
            "rust": "fn name(args) -> T { ... }",
            "web": "function name(args) { ... }",
        },
    ),
    AliasEntry(
        canonical="lam",
        aliases=("lambda", "anon", "anonfn", "mklam"),
        category="expression",
        tier="core",
        description="Inline lambda expression keyword.",
        target_forms={
            "python": "lambda a: expr",
            "js": "(a) => expr",
            "rust": "|a| expr",
            "web": "(a) => expr",
        },
    ),
    AliasEntry(
        canonical="ret",
        aliases=("rtn", "return", "giveback"),
        category="statement",
        tier="core",
        description="Return statement keyword.",
        target_forms={
            "python": "return expr",
            "js": "return expr;",
            "rust": "return expr;",
            "web": "return expr;",
        },
    ),
    AliasEntry(
        canonical="if",
        aliases=("iff", "when", "cond"),
        category="statement",
        tier="core",
        description="Conditional statement keyword.",
        target_forms={
            "python": "if cond: ... else: ...",
            "js": "if (cond) { ... } else { ... }",
            "rust": "if cond { ... } else { ... }",
            "web": "if (cond) { ... } else { ... }",
        },
    ),
    AliasEntry(
        canonical="loop",
        aliases=("lp", "repeat", "forloop", "iter"),
        category="statement",
        tier="core",
        description="Range loop statement keyword.",
        target_forms={
            "python": "for i in range(start, end): ...",
            "js": "for (let i = start; i < end; i++) { ... }",
            "rust": "for i in (start)..(end) { ... }",
            "web": "for (let i = start; i < end; i++) { ... }",
        },
    ),
    AliasEntry(
        canonical="in",
        aliases=("within",),
        category="statement",
        tier="core",
        description="Loop range delimiter keyword.",
        target_forms={
            "python": "range(start, end)",
            "js": "for init; test; update",
            "rust": "(start)..(end)",
            "web": "for init; test; update",
        },
    ),
    AliasEntry(
        canonical="print",
        aliases=("prnt", "echo", "say", "log"),
        category="builtin",
        tier="core",
        description="Portable print builtin.",
        target_forms={
            "python": "print(value)",
            "js": "print(value) (helper -> console.log)",
            "rust": "println!(\"{:?}\", value)",
            "web": "print(value) (helper -> DOM + console)",
        },
    ),
    AliasEntry(
        canonical="true",
        aliases=("yes", "on"),
        category="literal",
        tier="extended",
        description="Boolean true literal.",
        target_forms={
            "python": "True",
            "js": "true",
            "rust": "true",
            "web": "true",
        },
    ),
    AliasEntry(
        canonical="false",
        aliases=("no", "off"),
        category="literal",
        tier="extended",
        description="Boolean false literal.",
        target_forms={
            "python": "False",
            "js": "false",
            "rust": "false",
            "web": "false",
        },
    ),
    AliasEntry(
        canonical="&&",
        aliases=("and",),
        category="operator",
        tier="extended",
        description="Logical AND operator.",
        target_forms={
            "python": "and",
            "js": "&&",
            "rust": "&&",
            "web": "&&",
        },
    ),
    AliasEntry(
        canonical="||",
        aliases=("or",),
        category="operator",
        tier="extended",
        description="Logical OR operator.",
        target_forms={
            "python": "or",
            "js": "||",
            "rust": "||",
            "web": "||",
        },
    ),
    AliasEntry(
        canonical="!",
        aliases=("not",),
        category="operator",
        tier="extended",
        description="Logical NOT operator.",
        target_forms={
            "python": "not",
            "js": "!",
            "rust": "!",
            "web": "!",
        },
    ),
    AliasEntry(
        canonical="==",
        aliases=("eq",),
        category="operator",
        tier="extended",
        description="Equality operator.",
        target_forms={
            "python": "==",
            "js": "==",
            "rust": "==",
            "web": "==",
        },
    ),
    AliasEntry(
        canonical="!=",
        aliases=("neq",),
        category="operator",
        tier="extended",
        description="Inequality operator.",
        target_forms={
            "python": "!=",
            "js": "!=",
            "rust": "!=",
            "web": "!=",
        },
    ),
    AliasEntry(
        canonical=">=",
        aliases=("gte",),
        category="operator",
        tier="extended",
        description="Greater-than-or-equal operator.",
        target_forms={
            "python": ">=",
            "js": ">=",
            "rust": ">=",
            "web": ">=",
        },
    ),
    AliasEntry(
        canonical="<=",
        aliases=("lte",),
        category="operator",
        tier="extended",
        description="Less-than-or-equal operator.",
        target_forms={
            "python": "<=",
            "js": "<=",
            "rust": "<=",
            "web": "<=",
        },
    ),
)


def validate_alias_mode(mode: str) -> str:
    """Validate and normalize alias mode."""
    normalized = mode.strip().lower()
    if normalized not in _ALIAS_MODES:
        raise ValueError(f"Unsupported alias mode '{mode}'. Expected one of: {', '.join(sorted(_ALIAS_MODES))}")
    return normalized


def alias_entries(mode: str = "core") -> list[AliasEntry]:
    """Return alias entries enabled for selected mode."""
    selected_mode = validate_alias_mode(mode)
    if selected_mode == "extended":
        return list(_ALIAS_ENTRIES)
    return [entry for entry in _ALIAS_ENTRIES if entry.tier == "core"]


def alias_lookup(mode: str = "core") -> dict[str, str]:
    """Return alias->canonical map for selected mode."""
    lookup: dict[str, str] = {}
    for entry in alias_entries(mode):
        for alias in entry.aliases:
            lookup[alias] = entry.canonical
    return lookup


def alias_catalog(mode: str = "core") -> list[dict[str, object]]:
    """JSON-friendly alias catalog for CLI/service/docs."""
    catalog: list[dict[str, object]] = []
    for entry in alias_entries(mode):
        catalog.append(
            {
                "canonical": entry.canonical,
                "aliases": list(entry.aliases),
                "category": entry.category,
                "tier": entry.tier,
                "description": entry.description,
                "target_forms": dict(entry.target_forms),
            }
        )
    return catalog
