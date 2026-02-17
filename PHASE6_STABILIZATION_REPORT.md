# Phase 6 Stabilization Report (ICL v2.0)

Date: February 17, 2026

## Scope
This report covers Phase 6:
- versioning consistency
- release artifact rebuild
- release packaging hardening

## Versioning Consistency
Validated and aligned:
- project/package version: `2.0.0` (`pyproject.toml`)
- service capabilities version: `2.0.0` (`icl/service.py`)
- MCP server info version: `2.0.0` (`icl/mcp_server.py`)

## Binary Naming Stabilization
- Standalone MCP spec now emits canonical binary name: `icl-mcp`
- Legacy spec filename retained for compatibility: `icp-mcp.spec`
- Legacy binary alias refreshed from canonical build:
  - `dist/icl-mcp` (primary)
  - `dist/icp-mcp` (compat alias copy)

## Packaging Hardening Fix
Issue fixed:
- local top-level folders (`tmp/`, `output/`) caused setuptools auto-discovery failure during build.

Fix applied:
- explicit package discovery in `pyproject.toml`:
  `[tool.setuptools.packages.find] include = ["icl*"]`

## Rebuilt Release Artifacts
Generated in `dist/`:
- `icl-mcp`
- `icp-mcp`
- `icl_lang-2.0.0-py3-none-any.whl`
- `icl_lang-2.0.0.tar.gz`

Checksums:
- `output/phase6/SHA256SUMS.txt`

Build logs:
- `output/phase6/pyinstaller_build.log`
- `output/phase6/python_build.log`

## Verification
- Full test suite: `python -m unittest discover -s tests -v`
- Result: `62 passed, 1 skipped`

## Phase 6 Status
Phase 6 is complete.
