# Codex Blocking Exec

Codex Blocking Exec ships a Codex `PreToolUse` hook for explicit long-running
Bash commands.

Use:

```bash
codex-block -- gh pr checks 123 --repo owner/repo --watch --interval 60
```

The hook only intercepts Bash commands whose first shell token is
`codex-block`. It runs the command after `--` synchronously inside the hook,
writes full combined stdout/stderr to `/tmp/codex-blocking-exec`, and rewrites
the original Bash tool call to a fast `printf` summary with the real exit code.

Normal Bash commands are untouched.

If the hook is disabled, missing, or untrusted, `codex-block` fails closed
instead of running the long command directly.

## Notes

- No plugin-specific hook timeout is configured. Codex applies its current
  default hook timeout.
- The hook is intentionally opt-in through the `codex-block --` prefix.
- Shell features such as pipes and redirects are not interpreted after `--`.
  Wrap complex commands in a shell explicitly, for example:

```bash
codex-block -- sh -lc 'make test 2>&1 | tee /tmp/test.log'
```
