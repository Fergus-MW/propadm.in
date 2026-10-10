# Submission TODO — Real-World Agents Hackathon (Sat 10 Oct 2026, London time)

Rules: https://docs.google.com/document/d/1VONrEJRnT3wO35qGhrwy0h_OjJ4iH2Qt40CCuquYMXI/

**Scoring (100):** correct outcomes + coverage 38.5 · demo 30 · judgement & safety 14 · engineering 10.5 · real-world applicability 7

## Before 16:30: build
- [ ] Agent handles the property-management workflow end to end using real tools/APIs
- [ ] Handles ambiguity, conflicting info, missing context, failed actions; escalates when a human should decide (escalating or doing nothing can be the right answer)
- [ ] Batch runner: processes a whole folder of unseen cases unattended, in parallel, and keeps going when one case fails
- [ ] Per case the system auto-writes `ANSWERS/<n>/ANSWER.md`, `REASONING.md` and a trace/log file showing: input received, actions taken, outputs/decisions, escalations, failures, final result
- [ ] Dry-run the runner on the provided cases end to end
- [ ] Freeze the code and demo video at 16:30 and submit them to the form

## 16:30–17:00: Reality Test
- [ ] Run the system on the unseen cases. Too many to do by hand: the system must do it
- [ ] Do NOT hand-edit or replace failed outputs; never fabricate results
- [ ] Commit `ANSWERS/` + logs/traces

## By 17:00: code + results freeze (record the commit hash)
- [ ] Public repo, readable by anyone without asking
- [ ] `LICENSE`: standard Apache 2.0 text
- [ ] No secrets committed (`.env` stays untracked)
- [ ] `README.md` covers:
  - [ ] what we built
  - [ ] the operational problem it solves
  - [ ] architecture
  - [ ] how to run it (prerequisites, install, config, env vars)
  - [ ] models, APIs and external services used
  - [ ] assumptions
  - [ ] known limitations
  - [ ] what we'd build next
- [ ] Evidence for anything judges can't access (logs, traces, screenshots)
- [ ] No text aimed at the judging model (prompt injection = zero points or disqualification)

## After 17:00: allowed additions only
- [ ] 60s demo video committed in the repo (Git LFS ok; an external link alone isn't enough), showing the real working product: problem, solution, key workflow, result
- [ ] LinkedIn post + X post (project name, what it does, repo link)
- [ ] `SUBMISSION.md` with post links (optional)
- [ ] Submit form: repo URL, team name, track, all member names, 17:00 commit hash, Reality Test results, video path, LinkedIn URL, X URL
- [ ] Ask organisers if there's also a live presentation at 17:00–19:00
