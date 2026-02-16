# Compiler Architecture

## Pipeline
Human intent source text flows through these deterministic phases:

1. Lexer (`icl/lexer.py`)
2. Parser (`icl/parser.py`)
3. Semantic analyzer (`icl/semantic.py`)
4. Intent graph builder (`icl/graph.py`)
5. Optional optimizer (`icl/optimize.py`)
6. Backend expansion (`icl/expanders/*.py`)

## Components

### Lexer
- Produces `Token` stream with `SourceSpan` provenance.
- Handles keywords, operators, literals, comments, and structured lexical errors.

### Parser
- Hybrid recursive-descent + Pratt expression parser.
- Supports panic-mode synchronization for multi-error resilience.
- Produces strongly typed AST nodes in `icl/ast.py`.

### Semantic Analyzer
- Builds lexical scopes and symbol tables.
- Performs binding validation and type inference.
- Enforces return context, function arity, annotation compatibility.

### Intent Graph Builder
- Converts AST to graph nodes and typed edges.
- Preserves statement ordering in edge metadata.
- Emits source-map node provenance for reversibility.

### Optimizer
- Constant folds operation nodes with literal operands.
- Removes dead assignments without references.
- Prunes orphan nodes after mutation.

### Backends
- Backend contract: `BackendEmitter.emit_module(graph, context) -> str`
- Built-ins:
  - Python backend
  - JavaScript backend
  - Rust scaffold backend

## Extensibility

### Plugin Manager (`icl/plugin.py`)
- Backend registration API.
- Dynamic plugin loader with `module[:symbol]` specs.
- Syntax plugin hooks:
  - `preprocess_source`
  - `transform_program`
- Macro plugin expansion for `#macro(args)` statements.

## Error Model
Structured errors by phase:
- Lex: `LEX*`
- Parse: `PAR*`
- Semantic/plugin: `SEM*`, `PLG*`
- CLI/internal: `CLI*`

Each diagnostic can include file/line/column span and hint text.

## Reversible Metadata
- Graph JSON (`icl/serialization.py`)
- Source map JSON (`icl/source_map.py`)

These artifacts are designed for future reverse compilation and intent-level diff tooling.
