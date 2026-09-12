#!/usr/bin/env python3
"""Read complete omp tool events without modifying their source."""

import json
from pathlib import Path


def _args_head(value):
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        except (TypeError, ValueError):
            text = str(value)
    return text.replace("\n", " ")[:80]


def scan_tools(path, offset):
    """Return completed tool calls after offset and the last complete-line offset."""
    path = Path(path)
    try:
        size = path.stat().st_size
        if offset < 0 or offset > size:
            offset = 0
        with path.open("rb") as stream:
            stream.seek(offset)
            data = stream.read()
    except OSError:
        return [], offset

    end = data.rfind(b"\n")
    if end < 0:
        return [], offset
    complete = data[: end + 1]
    starts = {}
    events = []
    for raw in complete.splitlines():
        try:
            event = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        call_id = event.get("toolCallId")
        if event.get("type") == "tool_execution_start":
            if call_id:
                starts[call_id] = event.get("args")
            continue
        if event.get("type") != "tool_execution_end":
            continue
        events.append({
            "name": event.get("toolName") or "",
            "args_head": _args_head(starts.get(call_id)),
            "ok": event.get("isError") is False,
        })
    return events, offset + len(complete)
