# Lys Marketplace

This repository is a Codex plugin marketplace.

## Install

Add the marketplace and install the plugin:

```bash
codex plugin marketplace add liyishuai/Lys-marketplace
codex plugin add blocking-exec@lys-marketplace
```

Then open the Codex plugin UI, enable the plugin, and review and trust its hook
definition. Codex does not automatically trust hooks bundled by plugins.

## Plugins

### Blocking Exec

`blocking-exec` ships a `PreToolUse` hook for Bash. When Codex calls Bash,
the hook runs the original command synchronously, writes combined stdout/stderr
to `/tmp/bx`, and rewrites the Bash tool call to replay that
captured output with the command's original exit code.

This is useful for long-running commands where Codex's normal command-yield loop
would otherwise wake the model repeatedly while the process is still running.

Notes:

- No plugin-specific hook timeout is configured; Codex applies its current
  default hook timeout.
- Commands that rely on interactive stdin are not a good fit for this hook.
