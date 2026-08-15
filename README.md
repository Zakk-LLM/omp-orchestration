# omp Orchestration Skill

English | [繁體中文](README.zh-TW.md)

A skill for driving a fleet of omp (oh-my-pi) workers from an orchestrating agent that keeps
planning, supervision, review, and shipping for itself. Third sibling of
[codex-orchestration](https://github.com/Zakk-LLM/codex-orchestration) and
[opencode-orchestration](https://github.com/Zakk-LLM/opencode-orchestration): same run
directory, same tiers, same review gate, same atomic integration, a different engine.

The division of labor is fixed. Workers produce code and drafts only. The orchestrator reads the
real diff, runs the tests, and writes the verdict; commits, merges, and releases stay with it.

## Requirements

- omp 17 or newer with a working provider
- Python 3.11 or newer
- Bash

## Install

```bash
git clone <repository-url> omp-orchestration
cd omp-orchestration
./install.sh
```

| Agent | Location |
|---|---|
| Claude | `~/.claude/skills/omp` |
| Codex | `${CODEX_HOME:-~/.codex}/skills/omp` |
| OpenCode | `~/.config/opencode/skills/omp` |
| omp | `${OMP_CONFIG_DIR:-~/.omp/agent}/skills/omp` |

## What this engine changes

**A real cost figure.** Every assistant message carries `usage.cost` in dollars, so `meta.json`
records what a run cost. Measured on one fixture: the same one-file fix cost $0.167 on the
flagship model and $0.0047 on the cheap one — a 35× spread that a token count alone hides.

**Tool withholding as the boundary.** `--tools` is an allowlist and a worker cannot call a tool
it was not given: a `read-only` worker has no `write`, `edit`, or `bash` at all.

**Sessions inside the run.** `--session-dir` keeps every session file in `<run>/sessions/`, so a
run directory is self-contained.

**A built-in deadline.** `--max-time` stops the session from the inside; the external `timeout`
is only the backstop.

**Roles as files.** `--role <name>` appends an agent definition from `~/.omp/agent/agents/` to
the system prompt.

**No sandbox**, like opencode: the allowlist is the entire boundary, so untrusted work does not
belong here. **No schema enforcement**: the wrapper appends the contract to the prompt and
validates the answer, exiting 65 on a violation. **No `web_search` in the allowlist**: `read`
accepts URLs, but a worker that must search needs `--permission full`.

## Usage

```bash
RUN=$(scripts/omp_new_run.sh add-auth-cache)
scripts/omp_agents.sh --list          # every engine's agents, machine-wide
scripts/omp_capacity.sh medium

scripts/omp_agent.sh --run-dir "$RUN" --label cache \
  --cwd /path/to/repo --worktree --permission workspace-write \
  --tier deep --timeout 1800 --stall 300 \
  --prompt-file "$RUN/agents/cache/prompt.md" --schema "$RUN/schema/impl.json"

scripts/omp_dispatch.sh --run-dir "$RUN" --jobs "$RUN/jobs.jsonl" --weight medium
scripts/omp_watch.sh "$RUN" --timeout 120 --peek
scripts/omp_verify.sh "$RUN" cache --check "pytest -q"
scripts/omp_merge.sh --run-dir "$RUN" --repo /path/to/repo --into main --check "pytest -q"
```

Every script documents its options under `--help`.

## Permission profiles

| Profile | Tools granted | Use for |
|---|---|---|
| `read-only` | `read, grep, glob, lsp, yield` | research, audits, review |
| `workspace-write` | plus `write, edit, bash, ast_edit` | implementation |
| `full` | every tool, MCP included | search-dependent work |
| `bypass` | every tool, approvals off | only in a workspace you would hand a shell to |

Every profile disables approvals, because print mode has nobody to answer a prompt and would
hang until the deadline. The allowlist, not an approval rule, is the boundary.

## Shared with the sibling toolkits

The agent cap is machine-wide across all three engines: they lock the same slot directory and
each counter reads every registry, so `AGENT_MAX_AGENTS` (default 5) is the total, not five
each. Tier-to-model bindings and the cap live in
`${XDG_CONFIG_HOME:-~/.config}/agent-orchestration.env`.

Tiers, dependency ordering, worktree isolation, bounded waiting, deadline warnings, the
regression-scope tool, the review gate, and atomic integration behave as documented in the
siblings. Read [SKILL.md](SKILL.md) and `references/`:

- [references/prompt-template.md](references/prompt-template.md)
- [references/schemas.md](references/schemas.md)
- [references/worktrees.md](references/worktrees.md)
- [references/review-gate.md](references/review-gate.md)
- [references/troubleshooting.md](references/troubleshooting.md)

## Known constraints

- `omp -p` waits on inherited stdin; the wrapper redirects it from `/dev/null`.
- `--tools` accepts a fixed vocabulary; an unknown name aborts the run before it starts.
- Session state is shared, so simultaneous launches are staggered behind a machine-wide lock and
  a `database is locked` failure retries with backoff.
- Two agents writing one checkout overwrite each other; worktrees and `PLAN.md` ownership
  prevent it.

## License

MIT
