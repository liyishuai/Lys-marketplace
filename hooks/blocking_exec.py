#!/usr/bin/env python3
"""PreToolUse hook for blocking all Bash commands until completion.

The hook runs the Bash command synchronously, records full output to /tmp, and
rewrites the original Bash tool call into a short summary command.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path


LOG_DIR = Path(os.environ.get("CODEX_BLOCK_LOG_DIR", "/tmp/codex-blocking-exec"))
TAIL_BYTES = int(os.environ.get("CODEX_BLOCK_TAIL_BYTES", "12000"))


def emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=True))


def allow_rewrite(command: str) -> None:
    emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "updatedInput": {"command": command},
            }
        }
    )


def tail_file(path: Path, limit: int) -> str:
    with path.open("rb") as fh:
        try:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - limit))
        except OSError:
            fh.seek(0)
        data = fh.read()
    return data.decode("utf-8", errors="replace")


def run_blocking(command: str, cwd: str | None, log_path: Path) -> int:
    with log_path.open("wb") as log:
        started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        log.write(f"$ {command}\nstarted_at: {started}\n\n".encode())
        log.flush()

        try:
            proc = subprocess.Popen(
                ["bash", "-lc", command],
                cwd=cwd or None,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        except OSError as exc:
            log.write(f"\nfailed_to_start: {exc}\n".encode())
            return 127

        return proc.wait()


def replacement_command(summary: str, rc: int) -> str:
    return f"printf '%s\\n' {shlex.quote(summary)}; exit {int(rc)}"


def main() -> int:
    payload = json.load(sys.stdin)
    if payload.get("hook_event_name") != "PreToolUse":
        return 0
    if payload.get("tool_name") != "Bash":
        return 0

    command = payload.get("tool_input", {}).get("command")
    if not isinstance(command, str):
        return 0

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    job_id = f"{int(time.time())}-{os.getpid()}"
    log_path = LOG_DIR / f"{job_id}.log"
    started_at = time.time()
    rc = run_blocking(command, payload.get("cwd"), log_path)
    duration_ms = int((time.time() - started_at) * 1000)
    output_tail = tail_file(log_path, TAIL_BYTES)

    summary = "\n".join(
        [
            "[codex-blocking-exec]",
            f"job_id: {job_id}",
            f"command: {command}",
            f"exit_code: {rc}",
            f"duration_ms: {duration_ms}",
            f"log: {log_path}",
            "",
            "--- output tail ---",
            output_tail,
        ]
    )

    allow_rewrite(replacement_command(summary, rc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
