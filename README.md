# Codex Marketplace

This repository is a Codex plugin marketplace.

## Codex Blocking Exec

Codex Blocking Exec ships a Codex `PreToolUse` hook that blocks on every Bash
command until the command exits.

When Codex calls Bash, the hook runs the original command synchronously inside
the hook, writes full combined stdout/stderr to `/tmp/codex-blocking-exec`, and
rewrites the Bash tool call to replay the captured output with the real exit
code. This avoids Codex's command-yield loop for long-running commands because
the wait happens before the Bash tool starts.

Example:

```bash
gh pr checks 123 --repo owner/repo --watch --interval 60
```

## Install

Install from GitHub:

```bash
codex plugin marketplace add liyishuai/codex-marketplace
codex plugin add codex-blocking-exec@codex-marketplace
```

After installation, open the Codex plugin UI, enable the plugin, and review and
trust its hook definition. Codex does not automatically trust hooks bundled by
plugins.

## Notes

- No plugin-specific hook timeout is configured. Codex applies its current
  default hook timeout.
- The hook rewrites every Bash command result to the captured command output.
- Commands that rely on interactive stdin are not a good fit for this hook.
