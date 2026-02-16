"""Serialization helpers for Intent Graph and compiler artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from icl.graph import IntentGraph
from icl.source_map import SourceMap


def graph_to_json(graph: IntentGraph, indent: int = 2) -> str:
    """Serialize an IntentGraph to JSON text."""
    return json.dumps(graph.to_dict(), indent=indent, sort_keys=True)


def graph_from_json(payload: str) -> IntentGraph:
    """Deserialize an IntentGraph from JSON text."""
    data = json.loads(payload)
    return IntentGraph.from_dict(data)


def write_graph(graph: IntentGraph, path: str | Path) -> None:
    """Write serialized graph JSON to path."""
    target = Path(path)
    target.write_text(graph_to_json(graph), encoding="utf-8")


def write_source_map(source_map: SourceMap, path: str | Path) -> None:
    """Write source map JSON to path."""
    target = Path(path)
    payload: dict[str, Any] = source_map.to_dict()
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
