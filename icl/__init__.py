"""ICL compiler package."""

from __future__ import annotations

from typing import Any


__all__ = [
    "build_plugin_manager",
    "dispatch_service",
    "CompileArtifacts",
    "check_source",
    "compile_file",
    "compile_source",
    "compress_source",
    "explain_source",
]


def build_plugin_manager(*args: Any, **kwargs: Any):
    from icl.main import build_plugin_manager as _build_plugin_manager

    return _build_plugin_manager(*args, **kwargs)


def dispatch_service(*args: Any, **kwargs: Any):
    from icl.service import dispatch as _dispatch

    return _dispatch(*args, **kwargs)


def compile_source(*args: Any, **kwargs: Any):
    from icl.main import compile_source as _compile_source

    return _compile_source(*args, **kwargs)


def compile_file(*args: Any, **kwargs: Any):
    from icl.main import compile_file as _compile_file

    return _compile_file(*args, **kwargs)


def check_source(*args: Any, **kwargs: Any):
    from icl.main import check_source as _check_source

    return _check_source(*args, **kwargs)


def explain_source(*args: Any, **kwargs: Any):
    from icl.main import explain_source as _explain_source

    return _explain_source(*args, **kwargs)


def compress_source(*args: Any, **kwargs: Any):
    from icl.main import compress_source as _compress_source

    return _compress_source(*args, **kwargs)


def __getattr__(name: str):
    if name == "CompileArtifacts":
        from icl.main import CompileArtifacts

        return CompileArtifacts
    raise AttributeError(name)
