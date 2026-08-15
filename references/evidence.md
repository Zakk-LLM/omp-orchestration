# Evidence behind the defaults

Measured against omp 17.3.4 on one machine and one provider while building this skill. Anything
not measured here is inherited from the sibling skills, whose evidence files carry their own
sources. Figures come from development runs whose directories were not retained, so they are
reproducible by re-running rather than by opening an artifact.

## The engine's contract

- `omp -p --mode=json` emits JSONL with `session`, `agent_start`, `turn_start`,
  `message_start`, `message_update`, `message_end`, `turn_end`, `agent_end`. The session id
  arrives on the first `session` event, so a run is resumable even when it later fails.
- Assistant `message_end` carries `usage` with `input`, `output`, `cacheRead`, `cacheWrite` and
  a `cost` breakdown in dollars. That cost is the only per-run money figure any of the three
  engines reports.
- Tool calls appear as content entries of type `toolCall`, with the arguments as a JSON string
  in `partialArgs`. The `edit` tool names its target inside that payload rather than in a path
  field, so file tracking parses it out.
- Print mode waits on inherited stdin, exactly like `codex exec` and `opencode run`. The wrapper
  redirects it from `/dev/null`.

## The tool allowlist

`--tools` accepts exactly `read, grep, glob, lsp, yield, write, edit, bash, ast_edit` plus the
experiment tools and any MCP tool names; an unknown name aborts the run before it starts, which
is how the `ast_grep` in the original handoff notes was caught. There is no `web_search` in that
vocabulary — search comes from MCP and therefore needs the unrestricted profile, while `read`
accepts a URL and covers fetching a page the spec names.

Verified: a worker given `read,grep,glob` could not modify a file and reported that it was
blocked. Withholding the tool is stronger than denying its use, because the model has nothing
to call.

## Cost per tier

The same one-file fix, same prompt, same repository:

| model | thinking | input tokens | cost |
|-------|----------|--------------|------|
| `gpt-5.6-sol` | high | 31,224 | $0.167 |
| `gpt-5.6-luna` | low | 20,838 | $0.0047 |

A 35× spread on a task where the cheap model produced the same correct diff. This is why the
tier ladder changes the model below `deep` and the thinking level above it, and why an unbound
`OMP_TIER_*` is a silent cost bug: without the binding every tier runs the config's default.

## Dispatch overhead

A one-word reply with no tool use metered at roughly 16.6K input tokens, against roughly 20K for
`codex exec` and 8K for `opencode run` on the same account. That fixed cost is paid on every
dispatch before the task begins, so trivial work belongs batched into fewer agents.

## Concurrency

Session state is shared, so simultaneous launches can lose to a busy database. Starts are
serialized behind a machine-wide lock, and a launch that died on a lock retries with backoff
only when the run produced no events. The agent cap is shared with the codex and opencode
toolkits: all three lock the same slot directory and each counter reads every registry.
