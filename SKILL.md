---
name: omp
description: Drive the omp (oh-my-pi) CLI as a fleet of worker agents while you stay the orchestrator and reviewer. Use when a task is large enough to split across parallel workers — feature implementation, refactors, bug hunts, test writing, documentation drafting, research, multi-file audits — or whenever the user asks to delegate work to omp. You write the plan, dispatch scoped agents, supervise, review every diff yourself, and own the commit, merge, and deploy steps that workers are never allowed to touch. Sibling of the `codex` and `opencode` skills: same workflow, same run directory, different engine.
---

# omp Orchestration

omp writes; you plan, supervise, review, and ship. Workers never commit, never push, never
deploy, and never decide that their own output is acceptable.

Same design as the `codex` and `opencode` skills — one run directory, tiers by difficulty,
dependency ordering, bounded waiting, an evidence-based review gate, atomic integration — with
omp as the engine. Only the engine-specific parts are marked below.

## What omp gives you that the others do not

**A real cost figure.** Every assistant message carries `usage.cost` in dollars, so `meta.json`
records what a run actually cost rather than a token count you have to price yourself. Measured:
the same one-file fix cost $0.167 on the flagship and $0.0047 on the cheap model — a 35× spread
that is invisible without this number.

**Tool withholding as the boundary.** `--tools` is an allowlist, and a worker cannot call a tool
it was not given. A `read-only` worker has no `write`, `edit`, or `bash` at all, which is
stronger than a permission rule that says no.

**Sessions inside the run.** `--session-dir` puts every session file in `<run>/sessions/`, so a
run directory is self-contained and a resume needs no global state.

**A built-in deadline.** `--max-time` stops the session cleanly from the inside; the external
`timeout` is only the backstop for a hang.

**Roles as files.** `--role <name>` appends an agent definition from `~/.omp/agent/agents/` to
the system prompt, so a worker persona lives in one reusable file.

## What it costs you

**No sandbox.** Like opencode and unlike codex, there is no OS-level confinement: the tool
allowlist is the entire boundary. Do not run untrusted work.

**No schema enforcement.** Print mode cannot force a shape. The wrapper appends the schema to
the prompt and validates the answer afterwards, exiting 65 and recording `schema_error` when it
does not parse.

**Search is not in the allowlist.** `--tools` accepts `read, grep, glob, lsp, yield, write,
edit, bash, ast_edit` and a few experiment tools; there is no `web_search` among them. The
`read` tool does take a URL, so a restricted worker can still fetch a page it is given, but a
worker that must *search* needs `--permission full`, where MCP search tools are available.

## Preflight

```sh
omp --version || echo "omp not installed — stop and tell the user"
"$OMP_SKILL/scripts/omp_agents.sh" --list      # every engine's agents, machine-wide
omp models aicardlc | head                     # models this config can actually reach
```

The cap is shared with the codex and opencode toolkits: all three lock the same slot directory
and all three counters read all three registries, so `AGENT_MAX_AGENTS` (default 5) is the
machine total. Machine-local settings — the cap, the tier-to-model bindings — live in
`${XDG_CONFIG_HOME:-~/.config}/agent-orchestration.env`, which every wrapper sources.

## When not to use this

Do the work yourself when it is a single obvious edit, a one-file read, or anything you can
finish in less time than writing the spec. Never dispatch git mechanics — `omp_worktrees.sh
--rebase` and `omp_merge.sh` do them in one command, and the spec forbids workers from running
them anyway. Fan out only when the work decomposes; your review capacity, not the worker count,
is the limit.

## Workflow

### 1. Create the run directory

```sh
RUN=$("$OMP_SKILL/scripts/omp_new_run.sh" add-auth-cache)
```

```
<run>/PLAN.md                 decomposition, write scopes, acceptance criteria
<run>/jobs.jsonl              the fan-out, one job per line
<run>/schema/<name>.json      output schemas
<run>/sessions/               omp session files for this run
<run>/worktrees/<label>/      that agent's isolated checkout, branch omp/<label>
<run>/agents/<label>/prompt.md NOTES.md events.jsonl stderr.log result.json|last.txt
                     thread.txt started.json meta.json verify.json
<run>/REVIEW.md               your verdict per agent
```

`OMP_RUNS_DIR` overrides the base; the default is `${XDG_CACHE_HOME:-~/.cache}/omp-runs`. Never
a tmpfs path.

### 2. Decompose, then declare the order

Split by file ownership. A dependent job is not dispatched until its dependencies succeed, and
is skipped when one fails:

```json
{"label": "api",    "tier": "deep",     "permission": "workspace-write", "worktree": true}
{"label": "client", "tier": "standard", "permission": "workspace-write", "worktree": true,
 "depends_on": ["api"]}
```

Order and atomicity are one design: work is only ever built on a state that exists — a
dependency's finished result, or the target's real commit. Unknown labels and cycles are
rejected before anything starts.

### 3. Write the task spec

One file per agent from [references/prompt-template.md](references/prompt-template.md), with the
scope fence, executable acceptance criteria, the live-notes block, and the prohibitions. Paste
the regression scope from `omp_impact.sh --repo <repo> --format md` instead of letting the worker
search for it; each agent runs the targeted tests and the full suite runs once at integration.

### 4. Pick the tier, the profile, and the limits

| `--tier` | `--thinking` | use for | `--timeout` |
|----------|--------------|---------|-------------|
| `cheap` | `low` | mechanical edits, renames, formatting, extraction | 300–600 |
| `standard` | `medium` | default: a contained feature, docs, tests for one module | 900–1800 |
| `deep` | `high` | changes across several files, non-obvious bugs, refactors | 1800–3600 |
| `frontier` | `xhigh` | architecture, concurrency, performance, vague requirements | 3600–7200 |
| `max` | `max` | one problem a `frontier` agent already failed twice | 7200+ |

A tier always sets the thinking level, and sets the model when `OMP_TIER_<TIER>_MODEL` is bound.
Below `deep` the model changes, above it the thinking does — the cheap model is an order of
magnitude cheaper per token, and a read-only worker's bill is almost all input.

| `--permission` | tools granted | use for |
|----------------|---------------|---------|
| `read-only` | `read, grep, glob, lsp, yield` | research, audits, review |
| `workspace-write` | plus `write, edit, bash, ast_edit` | implementation |
| `full` | every tool, MCP included | search-dependent work, with care |
| `bypass` | every tool, approvals off | only in a workspace you would hand a shell to |

Every profile runs with approvals disabled, because a print-mode run has nobody to answer a
prompt and would sit until the deadline. That is exactly why the allowlist, not an approval
rule, is the boundary.

### 5. Dispatch

```sh
"$OMP_SKILL/scripts/omp_dispatch.sh" --run-dir "$RUN" --jobs "$RUN/jobs.jsonl" \
  --weight medium --max 4        # --dry-run prints the commands first
```

Engine-specific rules:

- stdin is closed; the prompt is an argument. An inherited stdin would keep the process waiting.
- `--max-time` is omp's own deadline and the wrapper sets it from `--timeout`; the external
  `timeout` fires 60 seconds later as the backstop.
- Starts are staggered behind a machine-wide lock and a launch that dies on `database is locked`
  is retried with backoff, only ever when the run produced no events.
- The session id comes from the first `session` event and lands in `thread.txt`.

### 6. Supervise without idling

```sh
"$OMP_SKILL/scripts/omp_watch.sh" "$RUN" --timeout 120 --peek
```

Exit 0 means agents changed state; 1 means the window is free for work that needs no agent; 2
means the run is finished; 3 means nothing was dispatched. Liveness is the event log's mtime plus
its last event read from the final 4 KB — never the whole log. `EXPIRING` and `QUIET` warn before
the guards fire. Correct a running worker with `omp_note.sh`, which its spec tells it to re-read.

**Never sit idle.** From the first dispatch to the last review you are either processing a
returned agent or doing work that does not depend on one. A regression you can fix now is fixed
ahead of the queue.

### 7. Review — the part you never delegate

An agent's report is a claim; a command you ran is evidence.

```sh
"$OMP_SKILL/scripts/omp_verify.sh" "$RUN" impl --check "pytest -q"
```

Read the diff, check every changed file against the declared scope, run each acceptance
criterion, and run a negative control. Check `meta.json.schema_error` and `usage.cost` — a
worker that cost a dollar for a rename was dispatched at the wrong tier. Protocol in
[references/review-gate.md](references/review-gate.md).

### 8. Fix rounds and continuation

```sh
"$OMP_SKILL/scripts/omp_agent.sh" --run-dir "$RUN" --label impl-fix1 \
  --resume "$(cat "$RUN/agents/impl/thread.txt")" --cwd /path/to/repo \
  --permission workspace-write --tier deep --prompt-file "$RUN/agents/impl-fix1/prompt.md"
```

Resuming replays the session, so continue one for the context it holds and start fresh when the
context is small, reconstructible, or already proven wrong. A transport failure is reported to
the user with its evidence rather than silently retried.

### 9. Integrate, then ship

```sh
"$OMP_SKILL/scripts/omp_merge.sh" --run-dir "$RUN" --repo /path/to/repo --into main \
  --check "pytest -q" --rebase
```

Atomic per branch and for the run: any conflict, failed rebase, or failed check returns the
target to the commit the run started from. This is where the full suite belongs. Check drift
first with `omp_worktrees.sh "$RUN" --drift main`. You perform every irreversible step, and
confirm with the user before anything outward-facing.

## References

- [references/prompt-template.md](references/prompt-template.md) — the task spec structure
- [references/schemas.md](references/schemas.md) — result shapes and how they are validated here
- [references/worktrees.md](references/worktrees.md) — isolating parallel writers, merging, cleanup
- [references/review-gate.md](references/review-gate.md) — the anti-optimism review protocol
- [references/troubleshooting.md](references/troubleshooting.md) — failure modes and recovery
