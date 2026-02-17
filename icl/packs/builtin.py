"""Built-in language pack implementations for ICL v2."""

from __future__ import annotations

from dataclasses import dataclass
import json

from icl.expanders.base import ExpansionContext
from icl.expanders.js_backend import JavaScriptBackend
from icl.expanders.python_backend import PythonBackend
from icl.expanders.rust_backend import RustBackend
from icl.language_pack import EmissionContext, LanguagePack, OutputBundle, PackManifest, PackRegistry
from icl.lowering import (
    LoweredAssignment,
    LoweredBinary,
    LoweredCall,
    LoweredExpr,
    LoweredExpressionStmt,
    LoweredFunction,
    LoweredIf,
    LoweredLiteral,
    LoweredLoop,
    LoweredModule,
    LoweredRef,
    LoweredReturn,
    LoweredStmt,
    LoweredUnary,
    lowered_to_graph,
)


COMMON_FEATURES = {
    "assignment": True,
    "expression_stmt": True,
    "if": True,
    "loop": True,
    "function": True,
    "return": True,
    "literal": True,
    "reference": True,
    "unary": True,
    "arithmetic": True,
    "comparison": True,
    "logic": True,
    "call": True,
    "at_call": True,
    "typed_annotation": True,
}

EXPERIMENTAL_FEATURES = {
    **COMMON_FEATURES,
    # Experimental pseudo packs intentionally fail on these until implemented per target.
    "typed_annotation": False,
    "logic": False,
    "at_call": False,
}


class LegacyBackendPack(LanguagePack):
    """Language pack wrapper that reuses existing graph emitters."""

    def __init__(self, manifest: PackManifest, backend: PythonBackend | JavaScriptBackend | RustBackend) -> None:
        self._manifest = manifest
        self._backend = backend

    @property
    def manifest(self) -> PackManifest:
        return self._manifest

    def emit(self, lowered: LoweredModule, context: EmissionContext) -> str:
        graph = lowered_to_graph(lowered)
        return self._backend.emit_module(
            graph,
            ExpansionContext(target=context.target, debug=context.debug, metadata=context.metadata),
        )


class JavaScriptPack(LanguagePack):
    """Stable JavaScript pack with runtime helper injection for runnable output."""

    def __init__(self) -> None:
        self._manifest = PackManifest(
            pack_id="icl.javascript",
            version="2.0.0",
            target="js",
            stability="stable",
            file_extension="js",
            block_model="braces",
            statement_termination="semicolon",
            type_strategy="gradual_symbolic_runtime",
            runtime_helpers=["print"],
            scaffolding={"primary": "main.js"},
            feature_coverage=dict(COMMON_FEATURES),
            aliases=["javascript", "node"],
        )
        self._backend = JavaScriptBackend()

    @property
    def manifest(self) -> PackManifest:
        return self._manifest

    def emit(self, lowered: LoweredModule, context: EmissionContext) -> str:
        graph = lowered_to_graph(lowered)
        body = self._backend.emit_module(
            graph,
            ExpansionContext(target=context.target, debug=context.debug, metadata=context.metadata),
        )
        if "print" not in lowered.required_helpers:
            return body

        helper = (
            "function print(value) {\n"
            "  console.log(value);\n"
            "}\n\n"
        )
        return helper + body


class WebPack(LanguagePack):
    """Web target emitting browser JavaScript and HTML/CSS scaffold."""

    def __init__(self) -> None:
        self._manifest = PackManifest(
            pack_id="icl.web.browser",
            version="2.0.0",
            target="web",
            stability="stable",
            file_extension="js",
            block_model="braces",
            statement_termination="semicolon",
            type_strategy="gradual_symbolic_runtime",
            runtime_helpers=["print"],
            scaffolding={"primary": "app.js", "html": "index.html", "css": "styles.css"},
            feature_coverage=dict(COMMON_FEATURES),
            aliases=["browser", "webapp"],
        )
        self._js_backend = JavaScriptBackend()

    @property
    def manifest(self) -> PackManifest:
        return self._manifest

    def emit(self, lowered: LoweredModule, context: EmissionContext) -> str:
        graph = lowered_to_graph(lowered)
        code = self._js_backend.emit_module(
            graph,
            ExpansionContext(target="js", debug=context.debug, metadata=context.metadata),
        )
        if "print" in lowered.required_helpers:
            helper = (
                "const __icl_output = document.getElementById('icl-output');\n"
                "function print(value) {\n"
                "  if (__icl_output) {\n"
                "    __icl_output.textContent += String(value) + '\\n';\n"
                "  }\n"
                "  console.log(value);\n"
                "}\n\n"
            )
            return helper + code
        return code

    def scaffold(self, emitted_code: str, context: EmissionContext) -> OutputBundle:
        html = """<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>ICL Web Output</title>
    <link rel=\"stylesheet\" href=\"styles.css\" />
  </head>
  <body>
    <main class=\"container\">
      <h1>ICL Web Output</h1>
      <pre id=\"icl-output\"></pre>
    </main>
    <script type=\"module\" src=\"app.js\"></script>
  </body>
</html>
"""
        css = """body {
  margin: 0;
  padding: 2rem;
  font-family: "JetBrains Mono", "Fira Code", monospace;
  background: radial-gradient(circle at top left, #f3f4f6, #dbeafe 50%, #bfdbfe);
  color: #0f172a;
}

.container {
  max-width: 64rem;
  margin: 0 auto;
  padding: 1.5rem;
  border: 1px solid #94a3b8;
  border-radius: 0.75rem;
  background: rgba(255, 255, 255, 0.92);
}

#icl-output {
  min-height: 10rem;
  padding: 1rem;
  border-radius: 0.5rem;
  background: #0f172a;
  color: #e2e8f0;
  overflow: auto;
}
"""
        return OutputBundle(
            primary_path="app.js",
            files={
                "index.html": html,
                "styles.css": css,
                "app.js": emitted_code,
            },
        )


@dataclass(frozen=True)
class PseudoProfile:
    """Small syntax profile for experimental emitters."""

    target: str
    extension: str
    comment_prefix: str
    function_keyword: str
    declaration_prefix: str


class PseudoPack(LanguagePack):
    """Experimental pseudo-emitter for broad language coverage."""

    def __init__(self, profile: PseudoProfile) -> None:
        self._profile = profile
        self._manifest = PackManifest(
            pack_id=f"icl.experimental.{profile.target}",
            version="2.0.0",
            target=profile.target,
            stability="experimental",
            file_extension=profile.extension,
            block_model="braces",
            statement_termination="semicolon",
            type_strategy="gradual_symbolic_best_effort",
            runtime_helpers=[],
            scaffolding={"primary": f"main.{profile.extension}"},
            feature_coverage=dict(EXPERIMENTAL_FEATURES),
            aliases=[],
        )

    @property
    def manifest(self) -> PackManifest:
        return self._manifest

    def emit(self, lowered: LoweredModule, context: EmissionContext) -> str:
        lines = [
            f"{self._profile.comment_prefix} experimental ICL pack: {self._profile.target}",
            f"{self._profile.comment_prefix} semantics-parity target, syntax is best-effort scaffold",
            "",
        ]
        for stmt in lowered.statements:
            lines.extend(self._emit_stmt(stmt, indent=0))
        return "\n".join(lines).rstrip() + "\n"

    def _emit_stmt(self, stmt: LoweredStmt, indent: int) -> list[str]:
        pad = "    " * indent

        if isinstance(stmt, LoweredAssignment):
            return [f"{pad}{self._profile.declaration_prefix}{stmt.name} = {self._emit_expr(stmt.value)};"]

        if isinstance(stmt, LoweredExpressionStmt):
            return [f"{pad}{self._emit_expr(stmt.expr)};"]

        if isinstance(stmt, LoweredIf):
            lines = [f"{pad}if ({self._emit_expr(stmt.condition)}) {{"]
            for body_stmt in stmt.then_block:
                lines.extend(self._emit_stmt(body_stmt, indent + 1))
            lines.append(f"{pad}}}")
            if stmt.else_block:
                lines[-1] = f"{pad}}} else {{"
                for body_stmt in stmt.else_block:
                    lines.extend(self._emit_stmt(body_stmt, indent + 1))
                lines.append(f"{pad}}}")
            return lines

        if isinstance(stmt, LoweredLoop):
            start = self._emit_expr(stmt.start)
            end = self._emit_expr(stmt.end)
            it = stmt.iterator
            lines = [f"{pad}for ({self._profile.declaration_prefix}{it} = {start}; {it} < {end}; {it}++) {{"]
            for body_stmt in stmt.body:
                lines.extend(self._emit_stmt(body_stmt, indent + 1))
            lines.append(f"{pad}}}")
            return lines

        if isinstance(stmt, LoweredFunction):
            params = ", ".join(param["name"] for param in stmt.params)
            lines = [f"{pad}{self._profile.function_keyword} {stmt.name}({params}) {{"]
            for body_stmt in stmt.body:
                lines.extend(self._emit_stmt(body_stmt, indent + 1))
            if not stmt.body:
                lines.append(f"{pad}    return 0;")
            lines.append(f"{pad}}}")
            return lines

        if isinstance(stmt, LoweredReturn):
            if stmt.value is None:
                return [f"{pad}return;"]
            return [f"{pad}return {self._emit_expr(stmt.value)};"]

        return [f"{pad}{self._profile.comment_prefix} unsupported statement: {type(stmt).__name__}"]

    def _emit_expr(self, expr: LoweredExpr) -> str:
        if isinstance(expr, LoweredLiteral):
            if isinstance(expr.value, bool):
                return "true" if expr.value else "false"
            return json.dumps(expr.value)

        if isinstance(expr, LoweredRef):
            return expr.name

        if isinstance(expr, LoweredUnary):
            operand = self._emit_expr(expr.operand)
            return f"({expr.operator}{operand})"

        if isinstance(expr, LoweredBinary):
            left = self._emit_expr(expr.left)
            right = self._emit_expr(expr.right)
            return f"({left} {expr.operator} {right})"

        if isinstance(expr, LoweredCall):
            callee = self._emit_expr(expr.callee)
            args = ", ".join(self._emit_expr(arg) for arg in expr.args or [])
            return f"{callee}({args})"

        return "null"


def build_builtin_pack_registry() -> PackRegistry:
    """Create a registry populated with stable and experimental built-in packs."""

    registry = PackRegistry()

    registry.register(
        LegacyBackendPack(
            manifest=PackManifest(
                pack_id="icl.python",
                version="2.0.0",
                target="python",
                stability="stable",
                file_extension="py",
                block_model="indent",
                statement_termination="newline",
                type_strategy="gradual_symbolic_runtime",
                runtime_helpers=[],
                scaffolding={"primary": "main.py"},
                feature_coverage=dict(COMMON_FEATURES),
                aliases=["py"],
            ),
            backend=PythonBackend(),
        )
    )

    registry.register(JavaScriptPack())

    registry.register(
        LegacyBackendPack(
            manifest=PackManifest(
                pack_id="icl.rust",
                version="2.0.0",
                target="rust",
                stability="stable",
                file_extension="rs",
                block_model="braces",
                statement_termination="semicolon",
                type_strategy="gradual_symbolic_scaffold",
                runtime_helpers=[],
                scaffolding={"primary": "main.rs"},
                feature_coverage=dict(COMMON_FEATURES),
                aliases=["rs"],
            ),
            backend=RustBackend(),
        )
    )

    registry.register(WebPack())

    experimental_profiles = [
        PseudoProfile(target="typescript", extension="ts", comment_prefix="//", function_keyword="function", declaration_prefix="let "),
        PseudoProfile(target="go", extension="go", comment_prefix="//", function_keyword="func", declaration_prefix="var "),
        PseudoProfile(target="java", extension="java", comment_prefix="//", function_keyword="static Object", declaration_prefix="var "),
        PseudoProfile(target="csharp", extension="cs", comment_prefix="//", function_keyword="static object", declaration_prefix="var "),
        PseudoProfile(target="cpp", extension="cpp", comment_prefix="//", function_keyword="auto", declaration_prefix="auto "),
        PseudoProfile(target="php", extension="php", comment_prefix="//", function_keyword="function", declaration_prefix="$"),
        PseudoProfile(target="ruby", extension="rb", comment_prefix="#", function_keyword="def", declaration_prefix=""),
        PseudoProfile(target="kotlin", extension="kt", comment_prefix="//", function_keyword="fun", declaration_prefix="var "),
        PseudoProfile(target="swift", extension="swift", comment_prefix="//", function_keyword="func", declaration_prefix="var "),
        PseudoProfile(target="lua", extension="lua", comment_prefix="--", function_keyword="function", declaration_prefix="local "),
        PseudoProfile(target="dart", extension="dart", comment_prefix="//", function_keyword="dynamic", declaration_prefix="var "),
    ]

    for profile in experimental_profiles:
        registry.register(PseudoPack(profile))

    return registry
