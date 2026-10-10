# Case runner

Processes a folder of property-management cases unattended and writes one answer folder per
case. Each case runs through the real Propadmin agent: the production orchestrator
(`services/agent/app/managed.py`), the production system prompt and skills, Claude Managed
Agents, and the production MCP gateway over an isolated graph.

```sh
uv run --with anthropic python -m reality_claude <cases-folder> --out ANSWERS
```

## What happens per case

1. Every file in the case folder is read: `index.md` first, `history.md` second, then
   attachments. PDF text is extracted; unreadable files are listed as unreadable.
2. A fresh in-memory graph gets the seeded skills and provider directory, `ticket:case` holding
   the whole case file, the property when the case file states its address, and sandbox
   contacts for the tenant, landlord, contractor and the agency staff team.
3. The orchestrator starts a run on the dedicated `Propadmin reality` agent. Its session reaches
   that graph's MCP gateway through one public tunnel at `/s<slot>/mcp`. Several cases run in
   parallel (`--slots`, default 6).
4. Email and phone providers are sandboxed: the agent's messages are recorded and the tool
   result says `SIMULATED`. Nothing is delivered to anyone.
5. The run ends when the agent finishes, sleeps waiting on someone, or hits `--timeout`.
6. If the agent ends its turn without a closing report, the same session is asked for one (no
   further tool use). If a session reports it could not reach the MCP gateway, the case is retried
   live once. If the live path still fails, the same system prompt and skills run as one direct model
   call. That answer is labelled **fallback** and its actions are proposals, not executions.

## Output

```
ANSWERS/
  README.md        index: run status, path (live/fallback), staff involvement, actions, failures
  run-log.json
  <n>/ANSWER.md    decision (the agent's own report), escalation to staff, actions with results,
                   full message texts, what failed, final ticket and plan state
  <n>/REASONING.md files received, skills consulted, plan with notes and evidence, every agent
                   message, the full tool trace
  <n>/trace.json   the complete run record
```

`<n>` comes from the digits in the case folder name (`003` → `3`), otherwise its position.
Every file is generated from the run record; nothing is written or corrected by hand.

## Requirements

- `ANTHROPIC_API_KEY` in `.env.local`, `.env` or the environment.
- `cloudflared` (`brew install cloudflared`) for a free Cloudflare quick tunnel; `ngrok` is the backup.
  The runner checks the tunnel through Cloudflare DNS-over-HTTPS because local resolvers (venue Wi-Fi)
  often cannot resolve a freshly created tunnel hostname.
- `uv sync` done for the workspace.

## Options

| Option | Use |
| --- | --- |
| `--slots N` | Cases in parallel (default 6) |
| `--timeout S` | Seconds per live run (default 360) |
| `--only 3,7` | Run selected cases |
| `--force` | Re-run cases that already have an `ANSWER.md` (otherwise they are skipped, so a re-run resumes) |
| `--hide-outcome` | Drop `Overview` and `Outcome` from `index.md`; for dry runs on solved public cases |
| `--fallback-only` | Skip Managed Agents entirely if the live path is down |

## Reality Test procedure

1. Put the unseen cases in a folder, for example `cases/reality/`.
2. Run `uv run --with anthropic python -m reality_claude cases/reality --out ANSWERS`.
3. If the run is interrupted, run the same command again: finished cases are kept.
4. Commit `ANSWERS/` as generated, failures included.
