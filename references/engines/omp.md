Read this page for omp tasks that depend on tier, thinking, timeout, permission, or tool-access behavior.
You need not read it for shared orchestration steps that do not depend on omp-specific flags or profiles.

# omp engine reference

| `--tier` | `--thinking` | use for | `--timeout` |
|----------|--------------|---------|-------------|
| `cheap` | `low` | mechanical edits, renames, formatting, extraction | 300–600 |
| `standard` | `medium` | default: a contained feature, docs, tests for one module | 900–1800 |
| `deep` | `high` | changes across several files, non-obvious bugs, refactors | 1800–3600 |
| `frontier` | `xhigh` | architecture, concurrency, performance, vague requirements | 3600–5400 |
| `max` | `max` | one problem a `frontier` agent already failed twice | 3600–5400 |

The `7200+` bands above are history: nothing runs past 5400.

**Hard ceiling: 5400 seconds (90 minutes) for any worker.** A worker still running past that is treated as suspect, non-essential work — repeated full gate runs, ablation of every hunk, a sixth version of the report — and is killed on sight, not waited for; every extra round re-reads the whole context and burns tokens by the hour. You finish from what is in its worktree: commit by theme, push, let CI be the gate. Cap the verification in the spec itself: one full gate run, two or three ablations of the hunks that matter, one report, and the sentence "do not repeat a full round".


A tier always sets the thinking level, and sets the model when `OMP_TIER_<TIER>_MODEL` is bound.

Which half of the ladder to climb first is a question about your models, not a rule. A mid-tier
model at maximum thinking is often better *and* cheaper than a top-tier model at moderate
thinking, and when that holds the tiers should exhaust the thinking levels on the mid model
before paying for the top one. Test it before assuming either way: dispatch the same hard task
twice, once at each configuration, compare the results against something checkable, and compare
`usage.cost`. Bind the answer in `OMP_TIER_<TIER>_MODEL` and leave this file provider-neutral.

Both halves of a tier are configurable, so the ladder is data rather than code: `OMP_TIER_<TIER>_MODEL` binds the model and `OMP_TIER_<TIER>_THINKING` overrides the thinking. Set both in the machine-local env file and no job has to carry `--thinking` by hand — a ladder that needs a flag on every dispatch is a ladder that will be forgotten on one.

What does not change: a read-only worker's bill is almost all input, so the cheapest model at
low thinking is right for most of a run, and promoting a task is a decision rather than a
default.

| `--permission` | tools granted | use for |
|----------------|---------------|---------|
| `read-only` | `read, grep, glob, lsp, yield` | research, review, any judgement reachable by reading |
| `workspace-write` | plus `write, edit, bash, ast_edit` | implementation |
| `full` | every tool, MCP included | search-dependent work, with care |
| `bypass` | every tool, approvals off | only in a workspace you would hand a shell to |

Every profile runs with approvals disabled, because a print-mode run has nobody to answer a
prompt and would sit until the deadline. That is exactly why the allowlist, not an approval
rule, is the boundary.

These profile names are omp's own. `read-only` here is a tool allowlist, not codex's kernel
sandbox, and omp has no `inspect` profile like opencode's — so an audit that must run tests or
a linter goes to `workspace-write` on this engine, or to a sibling. Reusing a sibling's mental
model of the same name is how a research agent ends up unable to run the check it was sent to
run.
