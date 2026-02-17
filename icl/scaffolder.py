"""Output scaffolding stage for emitted target code."""

from __future__ import annotations

from pathlib import Path

from icl.errors import CLIError
from icl.language_pack import EmissionContext, LanguagePack, OutputBundle


def scaffold_output(pack: LanguagePack, code: str, *, target: str, debug: bool = False) -> OutputBundle:
    """Run the pack scaffolding stage and return output bundle."""
    context = EmissionContext(target=target, debug=debug)
    return pack.scaffold(code, context)


def write_bundle(bundle: OutputBundle, output_path: str | Path | None = None) -> str:
    """Write scaffolded bundle to output path and return primary output text."""
    if output_path is None:
        return bundle.code

    output = Path(output_path)

    if output.suffix:
        if len(bundle.files) > 1:
            raise CLIError(
                code="CLI010",
                message=f"Output path '{output}' must be a directory for multi-file target artifacts.",
                span=None,
                hint="Use -o <directory> for targets like web that emit multiple files.",
            )
        output.write_text(bundle.code, encoding="utf-8")
        return bundle.code

    output.mkdir(parents=True, exist_ok=True)
    for relative_path, body in bundle.files.items():
        file_path = output / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(body, encoding="utf-8")
    return bundle.code
