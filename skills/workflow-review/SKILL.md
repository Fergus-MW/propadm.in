---
name: workflow-review
description: Decide when a skill's workflow has a real problem worth reporting, and when to propose a change to it. Use whenever a skill step failed, was wrong, or had to be improvised.
---

# Review a workflow

You never edit a live skill. You report issues and propose changes; an admin approves.

## Flag an issue (`report_workflow_issue`) when
- a step in a skill failed or produced the wrong outcome;
- the skill's instructions contradicted what actually happened (wrong contact route, outdated process, missing case);
- you had to improvise a step the skill doesn't cover;
- a tenant, contractor or admin complained about something a skill step caused;
- the same workaround was needed more than once.
- a ledger correction (reversal) was required because of following a skill;
  link the original entry, reversing entry and evidence to that skill.

## Don't flag
One-off external failures (a site was down, a call dropped), mistakes in the source data rather than the workflow, or preferences with no effect on outcome.

## Severity
- critical: could cause harm, safety or legal exposure (e.g. an emergency handled as routine)
- high: the task failed or a person was misled
- medium: extra steps or delay
- low: wording or clarity

Categories: wrong_step, missing_step, outdated_info, ambiguous_instruction, tool_failure, policy_gap. Check `list_workflow_issues` first; reporting the same title again adds an occurrence and your evidence.

## Propose a change (`propose_skill_change`) when
The issue is critical or high, or a medium/low issue has 3+ occurrences, and you can name a concrete fix you're confident in. Otherwise flag only.

A proposal contains the full new SKILL.md (from `get_skill`), reasoning that cites the issues and evidence (calls, emails, tickets, chunks), the expected effect, and the risks or cases the change could break. Change only what the issues require, and reference at least one issue id.
