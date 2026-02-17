"""Language pack contracts and registry for ICL v2."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
import importlib
from types import ModuleType
from typing import Any

from icl.errors import CLIError
from icl.lowering import LoweredModule


VALID_STABILITIES = {"experimental", "beta", "stable"}


@dataclass(frozen=True)
class PackManifest:
    """Declarative metadata for target language packs."""

    pack_id: str
    version: str
    target: str
    stability: str
    file_extension: str
    block_model: str
    statement_termination: str
    type_strategy: str
    runtime_helpers: list[str]
    scaffolding: dict[str, Any]
    feature_coverage: dict[str, bool]
    aliases: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EmissionContext:
    """Context passed into language pack emit/scaffold calls."""

    target: str
    debug: bool = False
    metadata: dict[str, Any] | None = None


@dataclass
class OutputBundle:
    """Scaffolded output payload for a target."""

    primary_path: str
    files: dict[str, str]

    @property
    def code(self) -> str:
        return self.files[self.primary_path]


class LanguagePack(ABC):
    """Language pack interface for emit + scaffold stages."""

    @property
    @abstractmethod
    def manifest(self) -> PackManifest:
        """Pack manifest used for registration and capability lookup."""

    @abstractmethod
    def emit(self, lowered: LoweredModule, context: EmissionContext) -> str:
        """Emit language source from lowered module."""

    def scaffold(self, emitted_code: str, context: EmissionContext) -> OutputBundle:
        """Default scaffolding for single-file outputs."""
        filename = self.manifest.scaffolding.get("primary", f"main.{self.manifest.file_extension}")
        return OutputBundle(primary_path=filename, files={filename: emitted_code})


@dataclass
class PackValidationResult:
    """Validation summary for pack manifests."""

    target: str
    ok: bool
    errors: list[str]


class PackRegistry:
    """Registry for language packs and lookup by target alias."""

    def __init__(self) -> None:
        self._packs: dict[str, LanguagePack] = {}
        self._alias_to_target: dict[str, str] = {}

    def register(self, pack: LanguagePack) -> None:
        manifest = pack.manifest
        self._validate_manifest_or_raise(manifest)

        self._packs[manifest.target] = pack
        self._alias_to_target[manifest.target] = manifest.target
        for alias in manifest.aliases:
            self._alias_to_target[alias] = manifest.target

    def has_target(self, target: str) -> bool:
        return target in self._alias_to_target

    def get(self, target: str) -> LanguagePack:
        canonical = self._alias_to_target.get(target)
        if canonical is None:
            raise CLIError(
                code="PACK001",
                message=f"Unknown target language pack '{target}'.",
                span=None,
                hint=f"Available packs: {', '.join(self.targets())}",
            )
        return self._packs[canonical]

    def targets(self, stability: str | None = None) -> list[str]:
        manifests = self.manifests(stability=stability)
        return sorted(manifest.target for manifest in manifests)

    def manifests(self, stability: str | None = None) -> list[PackManifest]:
        manifests = [pack.manifest for pack in self._packs.values()]
        if stability is not None:
            manifests = [manifest for manifest in manifests if manifest.stability == stability]
        return sorted(manifests, key=lambda item: item.target)

    def validate(self, target: str | None = None) -> list[PackValidationResult]:
        manifests = self.manifests()
        if target is not None:
            pack = self.get(target)
            manifests = [pack.manifest]

        results: list[PackValidationResult] = []
        for manifest in manifests:
            errors = self._validate_manifest(manifest)
            results.append(PackValidationResult(target=manifest.target, ok=not errors, errors=errors))
        return results

    def _validate_manifest_or_raise(self, manifest: PackManifest) -> None:
        errors = self._validate_manifest(manifest)
        if errors:
            raise CLIError(
                code="PACK002",
                message=f"Invalid language pack manifest for target '{manifest.target}'.",
                span=None,
                hint="; ".join(errors),
            )

    @staticmethod
    def _validate_manifest(manifest: PackManifest) -> list[str]:
        errors: list[str] = []
        if not manifest.pack_id.strip():
            errors.append("pack_id is required")
        if not manifest.version.strip():
            errors.append("version is required")
        if not manifest.target.strip():
            errors.append("target is required")
        if manifest.stability not in VALID_STABILITIES:
            errors.append("stability must be one of: experimental, beta, stable")
        if not manifest.file_extension.strip():
            errors.append("file_extension is required")
        if not manifest.block_model.strip():
            errors.append("block_model is required")
        if not manifest.statement_termination.strip():
            errors.append("statement_termination is required")
        if not manifest.type_strategy.strip():
            errors.append("type_strategy is required")
        if not isinstance(manifest.feature_coverage, dict):
            errors.append("feature_coverage must be a mapping")
        return errors


def load_pack_spec(registry: PackRegistry, spec: str) -> None:
    """Load custom language pack from module[:symbol] spec."""
    module_name, symbol_name = _split_spec(spec)

    try:
        module = importlib.import_module(module_name)
    except Exception as exc:  # pragma: no cover - import failure path
        raise CLIError(
            code="PACK003",
            message=f"Failed to import pack module '{module_name}': {exc}",
            span=None,
            hint="Ensure the module is importable and on PYTHONPATH.",
        ) from exc

    if symbol_name is None:
        target_obj: Any = module
    else:
        if not hasattr(module, symbol_name):
            raise CLIError(
                code="PACK004",
                message=f"Pack symbol '{symbol_name}' not found in module '{module_name}'.",
                span=None,
                hint="Use module[:symbol] with an exported pack object or register function.",
            )
        target_obj = getattr(module, symbol_name)

    _apply_loaded_pack_object(registry, target_obj, spec)


def load_pack_specs(registry: PackRegistry, specs: list[str]) -> None:
    """Load multiple custom pack specs into the registry."""
    for spec in specs:
        load_pack_spec(registry, spec)


def _split_spec(spec: str) -> tuple[str, str | None]:
    if not spec.strip():
        raise CLIError(code="PACK005", message="Pack spec cannot be empty.", span=None, hint="Use module[:symbol].")

    if ":" not in spec:
        return spec.strip(), "register"

    module_name, symbol_name = spec.split(":", 1)
    symbol = symbol_name.strip() or None
    return module_name.strip(), symbol


def _apply_loaded_pack_object(registry: PackRegistry, obj: Any, spec: str) -> None:
    if isinstance(obj, LanguagePack):
        registry.register(obj)
        return

    if isinstance(obj, (list, tuple, set)):
        for item in obj:
            _apply_loaded_pack_object(registry, item, spec)
        return

    if callable(obj):
        _apply_pack_callable(registry, obj, spec)
        return

    if isinstance(obj, ModuleType) and hasattr(obj, "register"):
        _apply_pack_callable(registry, getattr(obj, "register"), spec)
        return

    raise CLIError(
        code="PACK006",
        message=f"Unsupported custom pack export type '{type(obj).__name__}' for spec '{spec}'.",
        span=None,
        hint="Export a LanguagePack, iterable of packs, or callable returning packs.",
    )


def _apply_pack_callable(registry: PackRegistry, fn: Any, spec: str) -> None:
    try:
        produced = fn()
    except TypeError:
        produced = fn(registry)
    except Exception as exc:
        raise CLIError(
            code="PACK007",
            message=f"Pack callable failed for spec '{spec}': {exc}",
            span=None,
            hint="Check custom pack callable signature and runtime errors.",
        ) from exc

    if produced is None:
        return
    _apply_loaded_pack_object(registry, produced, spec)
