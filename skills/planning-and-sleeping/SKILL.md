---
name: planning-and-sleeping
description: Plan any task with more than one action, tick steps off with evidence, and sleep instead of waiting. Use at the start of every task and on every wake-up.
---

# Plan and sleep

## On every start or wake-up
1. Call `get_plan` first. The wake message says why you woke (timer, email reply, call ended, ticket update) and carries the new data.
2. No plan and the task needs more than one action: call `create_plan(goal, steps)` before doing anything else.

## Working the plan
- Exactly one step is `in_progress` at a time. Move it to `in_progress` before acting on it.
- Mark a step `done` only after the action it describes succeeded, and pass the tool result as `evidence`.
- A step you cannot finish yet is `blocked` with a note saying what it waits for. A step that no longer applies is `skipped` with the reason.
- New information changes the work: `add_step` for one extra step, `revise_plan` (with a reason) to reorder or rewrite. Earlier versions are kept.

## Sleeping
- Never poll or wait inside a turn. When the next step depends on someone else (a reply, a callback, a visit), leave the current step `in_progress` or `blocked`, then call `sleep(minutes, wake_on, reason)` and end your turn.
- `wake_on` lists the ids that should wake you early: email thread ids, call ids, ticket ids, entity ids.
- `minutes` is capped at 10. You always wake within 10 minutes; if nothing changed, check once and sleep again.

## Finishing
The run ends only when every step is `done` or `skipped` with a reason. Ending a turn with open steps schedules a 10-minute wake-up automatically.
