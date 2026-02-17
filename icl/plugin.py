"""Plugin interfaces and manager for ICL extensibility."""

from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import replace
import importlib
import inspect
from types import ModuleType
from typing import Any

from icl.ast import FunctionDefStmt, IfStmt, LoopStmt, MacroStmt, Program, Stmt
from icl.errors import SemanticError
from icl.expanders.base import BackendEmitter


class BackendPlugin(ABC):
    """Factory plugin that provides backend emitters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable backend identifier used by CLI selection."""

    @abstractmethod
    def create_emitter(self) -> BackendEmitter:
        """Construct backend emitter instance."""


class MacroPlugin(ABC):
    """Macro expansion hook for `#macro(args)` statements."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Macro identifier without leading '#'."""

    @abstractmethod
    def expand(self, stmt: MacroStmt) -> list[Stmt]:
        """Expand macro invocation into one or more statements."""


class SyntaxPlugin(ABC):
    """Syntax extension hooks before and after parse."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable plugin name."""

    def preprocess_source(self, source: str) -> str:
        """Optional source rewrite pass before lexing."""
        return source

    def transform_program(self, program: Program) -> Program:
        """Optional AST transform pass after parse."""
        return program


class PluginManager:
    """Registry and orchestration for compiler plugins."""

    def __init__(self) -> None:
        self._backends: dict[str, BackendEmitter] = {}
        self._macro_plugins: dict[str, MacroPlugin] = {}
        self._syntax_plugins: list[SyntaxPlugin] = []
        self._syntax_metadata: dict[str, Any] = {}

    def register_backend(self, name: str, emitter: BackendEmitter) -> None:
        """Register target backend emitter by name."""
        self._backends[name] = emitter

    def register_backend_plugin(self, plugin: BackendPlugin) -> None:
        """Register backend from backend plugin factory."""
        self.register_backend(plugin.name, plugin.create_emitter())

    def register_macro(self, plugin: MacroPlugin) -> None:
        """Register macro plugin."""
        self._macro_plugins[plugin.name] = plugin

    def register_syntax(self, plugin: SyntaxPlugin) -> None:
        """Register syntax extension plugin."""
        self._syntax_plugins.append(plugin)

    def preprocess_source(self, source: str) -> str:
        """Apply pre-lexing syntax plugin transformations."""
        updated = source
        self._syntax_metadata = {}
        for plugin in self._syntax_plugins:
            updated = plugin.preprocess_source(updated)
            if hasattr(plugin, "metadata"):
                raw_metadata = getattr(plugin, "metadata")
                if callable(raw_metadata):
                    self._syntax_metadata[plugin.name] = raw_metadata()
        return updated

    def transform_program(self, program: Program) -> Program:
        """Apply post-parse syntax plugin transformations."""
        updated = program
        for plugin in self._syntax_plugins:
            updated = plugin.transform_program(updated)
        return updated

    def metadata_snapshot(self) -> dict[str, Any]:
        """Return metadata produced by the most recent syntax preprocessing pass."""
        return deepcopy(self._syntax_metadata)

    def expand_macros(self, program: Program) -> Program:
        """Expand macro statements recursively using registered macro plugins."""
        expanded: list[Stmt] = []
        for stmt in program.statements:
            expanded.extend(self._expand_stmt(stmt))
        return replace(program, statements=expanded)

    def get_backend(self, name: str) -> BackendEmitter:
        """Resolve backend emitter by target name."""
        backend = self._backends.get(name)
        if backend is None:
            raise SemanticError(
                code="PLG001",
                message=f"Unknown backend target '{name}'.",
                span=None,
                hint=f"Available targets: {', '.join(sorted(self._backends.keys()))}",
            )
        return backend

    def available_backends(self) -> list[str]:
        """List available backend names."""
        return sorted(self._backends.keys())

    def _expand_stmt(self, stmt: Stmt) -> list[Stmt]:
        if isinstance(stmt, MacroStmt):
            plugin = self._macro_plugins.get(stmt.name)
            if plugin is None:
                raise SemanticError(
                    code="PLG002",
                    message=f"No macro plugin registered for '#{stmt.name}'.",
                    span=stmt.span,
                    hint="Register a macro plugin before compilation.",
                )
            result: list[Stmt] = []
            for produced in plugin.expand(stmt):
                result.extend(self._expand_stmt(produced))
            return result

        if isinstance(stmt, IfStmt):
            then_expanded: list[Stmt] = []
            else_expanded: list[Stmt] = []
            for item in stmt.then_block:
                then_expanded.extend(self._expand_stmt(item))
            for item in stmt.else_block:
                else_expanded.extend(self._expand_stmt(item))
            return [replace(stmt, then_block=then_expanded, else_block=else_expanded)]

        if isinstance(stmt, LoopStmt):
            body_expanded: list[Stmt] = []
            for item in stmt.body:
                body_expanded.extend(self._expand_stmt(item))
            return [replace(stmt, body=body_expanded)]

        if isinstance(stmt, FunctionDefStmt):
            body_expanded: list[Stmt] = []
            for item in stmt.body:
                body_expanded.extend(self._expand_stmt(item))
            return [replace(stmt, body=body_expanded)]

        return [stmt]


def load_plugin_spec(manager: PluginManager, spec: str) -> None:
    """Load and apply a plugin spec in `module[:symbol]` format.

    Behavior:
    - `module` implies symbol `register`
    - symbol may be a callable, plugin instance, backend emitter, or iterable of these
    - callable may accept either no args or one `PluginManager` arg
    """
    module_name, symbol_name = _split_plugin_spec(spec)
    module = _import_plugin_module(module_name, spec)

    if symbol_name is None:
        target: Any = module
    else:
        if not hasattr(module, symbol_name):
            raise SemanticError(
                code="PLG003",
                message=f"Plugin symbol '{symbol_name}' not found in module '{module_name}'.",
                span=None,
                hint="Use module[:symbol] with an exported callable/object.",
            )
        target = getattr(module, symbol_name)

    _apply_loaded_object(manager, target, spec)


def _split_plugin_spec(spec: str) -> tuple[str, str | None]:
    if not spec.strip():
        raise SemanticError(
            code="PLG004",
            message="Plugin spec cannot be empty.",
            span=None,
            hint="Use --plugin module:register",
        )

    if ":" not in spec:
        return spec, "register"

    module_name, symbol_name = spec.split(":", 1)
    symbol = symbol_name.strip() or None
    return module_name.strip(), symbol


def _import_plugin_module(module_name: str, spec: str) -> ModuleType:
    try:
        return importlib.import_module(module_name)
    except Exception as exc:  # pragma: no cover - import failure path
        raise SemanticError(
            code="PLG005",
            message=f"Failed to import plugin module '{module_name}' from spec '{spec}': {exc}",
            span=None,
            hint="Ensure module is on PYTHONPATH and importable.",
        ) from exc


def _apply_loaded_object(manager: PluginManager, obj: Any, spec: str) -> None:
    if isinstance(obj, BackendPlugin):
        manager.register_backend_plugin(obj)
        return

    if isinstance(obj, MacroPlugin):
        manager.register_macro(obj)
        return

    if isinstance(obj, SyntaxPlugin):
        manager.register_syntax(obj)
        return

    if isinstance(obj, BackendEmitter):
        manager.register_backend(obj.name, obj)
        return

    if isinstance(obj, (list, tuple, set)):
        for item in obj:
            _apply_loaded_object(manager, item, spec)
        return

    if callable(obj):
        _apply_callable(manager, obj, spec)
        return

    if isinstance(obj, ModuleType):
        if hasattr(obj, "register"):
            _apply_callable(manager, getattr(obj, "register"), spec)
            return

    raise SemanticError(
        code="PLG006",
        message=f"Unsupported plugin export type '{type(obj).__name__}' for spec '{spec}'.",
        span=None,
        hint="Export a register function, plugin instance, backend emitter, or iterable.",
    )


def _apply_callable(manager: PluginManager, fn: Any, spec: str) -> None:
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        sig = None

    result: Any
    try:
        if sig is None:
            result = fn(manager)
        else:
            positional = [
                p
                for p in sig.parameters.values()
                if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
            ]
            if len(positional) == 0:
                result = fn()
            elif len(positional) == 1:
                result = fn(manager)
            else:
                raise SemanticError(
                    code="PLG007",
                    message=f"Plugin callable in spec '{spec}' has unsupported signature '{sig}'.",
                    span=None,
                    hint="Use zero-arg factory or one-arg register(manager) callable.",
                )
    except SemanticError:
        raise
    except Exception as exc:
        raise SemanticError(
            code="PLG008",
            message=f"Plugin callable execution failed for spec '{spec}': {exc}",
            span=None,
            hint="Inspect plugin code and callable signature.",
        ) from exc

    if result is None:
        return

    _apply_loaded_object(manager, result, spec)


def load_plugins(manager: PluginManager, specs: list[str]) -> None:
    """Load a list of plugin specs into a manager."""
    for spec in specs:
        load_plugin_spec(manager, spec)
