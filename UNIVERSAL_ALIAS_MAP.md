# Universal Natural Alias Map (ICL v2.0)

This file defines the natural alias layer implemented in the current codebase.

## Activation
- CLI: `--natural` (off by default)
- Mode: `--alias-mode core|extended` (default: `core`)
- Service/MCP: `natural_aliases: true`, optional `alias_mode`

## Canonical Command Map (Core Mode)
| Canonical ICL | Natural Aliases | Category | Python Output Shape | JS/Web Output Shape | Rust Output Shape |
|---|---|---|---|---|---|
| `fn` | `mkfn`, `makefn`, `defn`, `func`, `function` | statement | `def name(args): ...` | `function name(args) { ... }` | `fn name(args) -> T { ... }` |
| `lam` | `lambda`, `anon`, `anonfn`, `mklam` | expression | `lambda a: expr` | `(a) => expr` | `\|a\| expr` |
| `ret` | `rtn`, `return`, `giveback` | statement | `return expr` | `return expr;` | `return expr;` |
| `if` | `iff`, `when`, `cond` | statement | `if cond: ... else: ...` | `if (cond) { ... } else { ... }` | `if cond { ... } else { ... }` |
| `loop` | `lp`, `repeat`, `forloop`, `iter` | statement | `for i in range(start, end): ...` | `for (let i = start; i < end; i++) { ... }` | `for i in (start)..(end) { ... }` |
| `in` | `within` | statement | `range(start, end)` | range in `for` header | range in `for` header |
| `print` | `prnt`, `echo`, `say`, `log` | builtin | `print(value)` | helper `print(value)` -> console/DOM | `println!("{:?}", value)` |

## Extended Mode Additions
| Canonical ICL | Natural Aliases | Category |
|---|---|---|
| `true` | `yes`, `on` | literal |
| `false` | `no`, `off` | literal |
| `&&` | `and` | operator |
| `\|\|` | `or` | operator |
| `!` | `not` | operator |
| `==` | `eq` | operator |
| `!=` | `neq` | operator |
| `>=` | `gte` | operator |
| `<=` | `lte` | operator |

## Full Construct Coverage vs Current Contract
| Construct | Alias Support | Notes |
|---|---|---|
| Assignment `name := expr` | canonical only | No textual assignment alias; keeps parse deterministic. |
| Typed assignment `name:Type := expr` | canonical only | Same as above. |
| Function def | yes | via `fn` aliases. |
| Lambda expr | yes | via `lam` aliases. |
| Conditional | yes | via `if` aliases. |
| Loop | yes | via `loop`, `in` aliases. |
| Return | yes | via `ret` aliases. |
| Macro `#name(args)` | canonical only | Macro names are plugin-owned; no global aliasing. |
| Call `name(args)` / `@name(args)` | builtin alias only | `print` aliases supported; `@` marker remains canonical. |
| Grouping / range / block punctuation | canonical only | `()`, `{}`, `..`, `?`, `:` unchanged. |
| Arithmetic/comparison symbols | canonical only | `+ - * / % < >` unchanged by alias layer. |
| Logic symbols | extended mode | word forms map to canonical operators. |

## Compatibility Notes (Current Codebase)
- Alias normalization runs before lexing through `NaturalAliasPlugin`.
- Strings and `//` comments are preserved without alias rewrites.
- Alias trace is available in service/MCP (`include_alias_trace`) and CLI explain (`--alias-trace`).
- Stable targets (`python`, `js`, `rust`, `web`) receive canonical IR/lowering after alias normalization.

## Quick Example
Input (natural):
```icl
mkfn add(a:Num,b:Num):Num => a + b;
inc := lambda(n:Num):Num => n + 1;
ok := yes and not no;
prnt(add(inc(1), 2));
```

Normalized canonical ICL:
```icl
fn add(a:Num,b:Num):Num => a + b;
inc := lam(n:Num):Num => n + 1;
ok := true && !false;
print(add(inc(1), 2));
```
