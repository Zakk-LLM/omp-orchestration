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


def repeated_failure(path, window=40, threshold=8):
    """A worker can emit events forever while getting nowhere: the same tool failing on the
    same input is progress to the stall guard and waste to everyone else. Reads the tail only."""
    try:
        size = path.stat().st_size
        with path.open("rb") as fh:
            fh.seek(max(0, size - 262144))
            lines = fh.read().decode(errors="replace").splitlines()
    except OSError:
        return None
    fails = []
    for line in lines:
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = ev.get("item") or ev.get("part") or {}
        state = item.get("state") or {}
        status = state.get("status")
        exit_code = item.get("exit_code")
        failed = status == "error" or (exit_code not in (0, None))
        if item.get("type") in ("tool", "command_execution", "tool_use") or status:
            key = f"{item.get('tool') or item.get('type')}"
            fails.append(key if failed else None)
    recent = [f for f in fails[-window:] if f]
    if not recent:
        return None
    top = max(set(recent), key=recent.count)
    n = recent.count(top)
    return (top, n) if n >= threshold else None


def last_event(path):
    try:
        size = path.stat().st_size
        with path.open("rb") as fh:
            fh.seek(max(0, size - 4096))
            lines = [l for l in fh.read().decode(errors="replace").splitlines() if l.startswith("{")]
    except OSError:
        return None
    for line in reversed(lines):
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = ev.get("item") or {}
        kind = item.get("type") or ev.get("type")
        detail = (item.get("command") or item.get("query") or item.get("text") or "")[:60]
        return f"{kind} {detail}".strip()
    return None
