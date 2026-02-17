# ICL Language Specification (v2)

This document summarizes the grammar. The normative behavioral source is `ICL_LANGUAGE_CONTRACT.md`.

## Grammar (EBNF)
```ebnf
program          = { opt_semicolons, statement, opt_semicolons }, EOF ;
opt_semicolons   = { ";" } ;

statement        = function_def
                 | if_stmt
                 | loop_stmt
                 | return_stmt
                 | macro_stmt
                 | assignment
                 | expression_stmt ;

assignment       = IDENT, [ ":", IDENT ], ":=", expression ;

function_def     = "fn", IDENT, "(", [ params ], ")", [ ":", IDENT ],
                   ( "=>", expression | block ) ;
params           = param, { ",", param } ;
param            = IDENT, [ ":", IDENT ] ;

if_stmt          = "if", expression, "?", block, [ ":", block ] ;
loop_stmt        = "loop", IDENT, "in", expression, "..", expression, block ;
return_stmt      = "ret", [ expression ] ;

macro_stmt       = "#", IDENT, "(", [ arguments ], ")" ;
arguments        = expression, { ",", expression } ;

expression_stmt  = expression ;

block            = "{", opt_semicolons,
                   { statement, opt_semicolons },
                   "}" ;

expression       = logical_or ;
logical_or       = logical_and, { "||", logical_and } ;
logical_and      = equality, { "&&", equality } ;
equality         = comparison, { ( "==" | "!=" ), comparison } ;
comparison       = term, { ( "<" | "<=" | ">" | ">=" ), term } ;
term             = factor, { ( "+" | "-" ), factor } ;
factor           = unary, { ( "*" | "/" | "%" ), unary } ;
unary            = ( "!" | "-" | "+" ), unary | postfix ;
postfix          = primary, { "(", [ arguments ], ")" } ;

primary          = NUMBER
                 | STRING
                 | "true"
                 | "false"
                 | IDENT
                 | "@", IDENT, "(", [ arguments ], ")"
                 | "(", expression, ")" ;
```

## Type Symbols
- `Num`, `Str`, `Bool`, `Any`, `Fn`, `Void`

## Semantics
See `ICL_LANGUAGE_CONTRACT.md` for scope, truthiness, type, and error model requirements.
