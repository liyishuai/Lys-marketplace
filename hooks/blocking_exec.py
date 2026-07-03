#!/usr/bin/env python3
"""PreToolUse hook for explicitly blocking long-running Bash commands.

The hook only intercepts commands whose first shell token is `codex-block`.
It runs the real command synchronously, records full output to /tmp, and
rewrites the original Bash tool call into a short summary command.
"""

from __future__ import annotations

import collections
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


def deny(reason: str) -> None:
    emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    )


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


def is_codex_block_token(token: str) -> bool:
    return Path(token).name == "codex-block"


def parse_command(command: str) -> tuple[list[str] | None, str | None]:
    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        return None, f"Unable to parse codex-block command: {exc}"

    if not tokens or not is_codex_block_token(tokens[0]):
        return [], None

    if len(tokens) < 3 or tokens[1] != "--":
        return None, "codex-block requires the form: codex-block -- <command> [args...]"

    real_argv = tokens[2:]
    if not real_argv:
        return None, "codex-block requires a command after --"

    return real_argv, None


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


def run_blocking(real_argv: list[str], cwd: str | None, log_path: Path) -> int:
    with log_path.open("wb") as log:
        started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        log.write(f"$ {shlex.join(real_argv)}\nstarted_at: {started}\n\n".encode())
        log.flush()

        try:
            proc = subprocess.Popen(
                real_argv,
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

    real_argv, error = parse_command(command)
    if error is not None:
        deny(error)
        return 0
    if not real_argv:
        return 0

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    job_id = f"{int(time.time())}-{os.getpid()}"
    log_path = LOG_DIR / f"{job_id}.log"
    started_at = time.time()
    rc = run_blocking(real_argv, payload.get("cwd"), log_path)
    duration_ms = int((time.time() - started_at) * 1000)
    output_tail = tail_file(log_path, TAIL_BYTES)

    summary = "\n".join(
        [
            "[codex-block]",
            f"job_id: {job_id}",
            f"command: {shlex.join(real_argv)}",
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
