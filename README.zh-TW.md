# omp Orchestration Skill

[English](README.md) | 繁體中文

這是把工作分派給多個 omp（oh-my-pi）工作代理的技能，協調者保留規劃、監督、審查與部署。它是 [codex-orchestration](https://github.com/Zakk-LLM/codex-orchestration) 與 [opencode-orchestration](https://github.com/Zakk-LLM/opencode-orchestration) 的第三個姊妹版：相同的執行目錄、難度分級、審查閘門與原子整合，底層引擎不同。

分工固定：工作代理只產出程式碼與草稿；協調者讀真實 diff、執行測試、寫審查結論；commit、merge、發佈由協調者執行。

## 要求

- omp 17 或更新版本，且已設定可用的供應商
- Python 3.11 或更新版本
- Bash

## 安裝

```bash
git clone <repository-url> omp-orchestration
cd omp-orchestration
./install.sh
```

| 代理 | 安裝位置 |
|---|---|
| Claude | `~/.claude/skills/omp` |
| Codex | `${CODEX_HOME:-~/.codex}/skills/omp` |
| OpenCode | `~/.config/opencode/skills/omp` |
| omp | `${OMP_CONFIG_DIR:-~/.omp/agent}/skills/omp` |

## 這個引擎的差異

**有真實金額**。每則助理訊息都帶 `usage.cost`，因此 `meta.json` 記錄的是實際花費而非需要自行換算的 token 數。實測同一個單檔修正：旗艦模型 $0.167，便宜模型 $0.0047，相差 35 倍——只看 token 數看不出這件事。

**以工具授予作為邊界**。`--tools` 是允許清單，工作代理無法呼叫沒有給它的工具：`read-only` 代理根本沒有 `write`、`edit`、`bash`。

**工作階段存在執行目錄內**。`--session-dir` 把 session 檔放進 `<run>/sessions/`，執行目錄因此自成一體。

**內建期限**。`--max-time` 從內部乾淨地結束工作階段，外層的 `timeout` 只是後備。

**角色即檔案**。`--role <name>` 把 `~/.omp/agent/agents/` 的代理定義附加到系統提示詞。

代價與 opencode 相同，有三項。

**沒有沙箱**：允許清單就是全部邊界，不受信任的工作不該放這裡。

**沒有結構化輸出強制**：包裝腳本在執行後驗證，不符合時離開碼 65。

**允許清單裡沒有 `web_search`**：`read` 可以讀 URL，但需要搜尋的工作要用 `--permission full`。

## 使用

```bash
RUN=$(scripts/omp_new_run.sh add-auth-cache)
scripts/omp_agents.sh --list
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

各腳本的 `--help` 列出全部選項。

## 權限設定檔

| 設定檔 | 授予的工具 | 用於 |
|---|---|---|
| `read-only` | `read, grep, glob, lsp, yield` | 研究、稽核、審查 |
| `workspace-write` | 再加上 `write, edit, bash, ast_edit` | 實作 |
| `full` | 全部工具，含 MCP | 需要搜尋的工作 |
| `bypass` | 全部工具且關閉核准 | 只用於你願意直接給出 shell 的工作區 |

所有設定檔都關閉核准提示，因為 print 模式沒有人能回答，會一直等到期限。邊界來自允許清單，不是核准規則。

## 與姊妹工具共用的部分

代理上限跨三個引擎共用：它們鎖定同一個名額目錄，每個計數器都讀取全部登記簿，所以 `AGENT_MAX_AGENTS`（預設 5）是機器總數，不是每個引擎各 5。難度級別對應的模型與上限寫在 `${XDG_CONFIG_HOME:-~/.config}/agent-orchestration.env`。

難度分級、依賴排序、worktree 隔離、有時限的等待、逾時預警、回歸範圍工具、審查閘門與原子整合，行為與姊妹版相同。詳見 [SKILL.md](SKILL.md) 與 `references/`：

- [references/prompt-template.md](references/prompt-template.md)
- [references/schemas.md](references/schemas.md)
- [references/worktrees.md](references/worktrees.md)
- [references/review-gate.md](references/review-gate.md)
- [references/troubleshooting.md](references/troubleshooting.md)

## 已知限制

- `omp -p` 會在繼承而來的 stdin 上等待，包裝腳本因此把 stdin 導向 `/dev/null`。
- `--tools` 只接受固定的工具名稱，寫錯會在執行開始前中止。
- 工作階段狀態共用，因此同時啟動會在機器層級的鎖後方錯開，遇到 `database is locked` 以退避重試。
- 兩個代理寫入同一個工作區會互相覆蓋，以 worktree 與 `PLAN.md` 的檔案歸屬預防。

## 授權

MIT
