# Workflow performance tuning

Open **Configure → Performance tuning** (`/tuning`). Start a loop to select a random
original corpus case, then a random cutoff whose next recorded event is an agent action.
External replies are observations supplied in the history, never prediction targets.
The default limit is 200 trials; adjust it before starting. The loop stops at ten distinct
passing transitions under the same skill versions, a trial limit, an error, or Stop tuning.
Ten passes are an operational stopping rule, not proof of performance on unseen cases.

Each prediction uses a fresh session of **Propadmin Workflow Tuner** and returns exactly
two fields: `answer` and `reasoning`. Reasoning is a concise explanation grounded in
history and skills. The answer describes one action including its recipient and channel;
the action is never executed. Only graph read tools are advertised, and the MCP gateway
also rejects communication, browser, raw query and operational write tools by name.

The API's existing `/mcp` endpoint remains the only graph interface. The selected case,
every revision with the same dataset/reference, associated original documents, chunks,
events, transitions, triplets, facts and provenance-derived entities are hidden. Every
other original case and ordinary graph record is readable. This tuning loop uses all
original corpus cases, including cases assigned to the older replay holdout split;
additional uploaded tests remain separate. The existing triplet retrieval tool continues
to rank training-split examples; graph search can read every other original case.
Runtime logs, earlier evaluations, private tests and historic skill versions are absent.
Shared documents are hidden even if another case references them. The supplied prefix
contains initial context and steps 1 through the cutoff; original case attachments are
not exposed. Skill contents and versions are frozen per trial. The store retains the
exclusion rule and frozen skills rather than another copy of the corpus.

Haiku compares the answer to the recorded next action using the existing semantic rubric.
A pass requires its overall score of at least 80, no critical error, and scores of at
least 80 for action, facts, recipient/channel and sequence. Wording need not match.
Reasoning is saved separately and used with the answer and grade for correction.

After a miss, the same restricted agent proposes one replacement in one skill. The old
text must occur exactly once; old and new text are each limited to 2,000 characters.
A new skill is permitted when none covers the workflow, with matching frontmatter and
at most 8,000 characters. Corrections must generalize the workflow without storing case
identifiers or reference answers. A fresh predictor first retests the failed sample with
the candidate, then reruns up to ten distinct previously successful samples. Any miss
rejects the candidate and leaves live skills unchanged. A successful candidate publishes
a new `skill_version` through the existing version mechanism, with an automatically
approved proposal, exact edit, validation evidence, audit change and training-case edges.
Publication checks optimistic versions. Skill changes reset the ten-pass streak.

## Unseen tests

Load a JSON object or an array of up to 20 cases, or paste history with `---` lines between
steps. The page offers a downloadable nine-step example. A JSON case has this shape:

```json
{
  "name": "New case",
  "initial_context": "Initial request and facts available at the start",
  "steps": ["Step 1", "Step 2", "Step 3"],
  "expected": "Optional reference next step"
}
```

The reference is hidden from the prediction session. Without it the page shows answer
and reasoning without claiming a passing grade. Private cases and evaluations are runtime
records only: no source files, chunks, entities or embeddings are ingested. These tests
never publish skill changes or contribute to the training success streak.

## Runtime and deployment

`make dev` starts a five-second tuning tick inside the existing API lifecycle and shuts
it down with the stack. No additional service or cloud credentials are needed to start
local development. Real prediction requires the model credentials; missing configuration
is reported explicitly before starting a job. There are no simulated model results.

Production uses the new Terraform `workflow-tuning` Cloud Scheduler job, invoking
`POST /internal/workflow-tuning/tick` once per minute with service authentication.
Progress is durable in the shared store; leases serialize ticks across API instances.
Polling the admin page only reads results, so closing the browser does not stop a loop.
The existing agent scheduler continues to relay provider sessions. Stop marks the job
stopped, revokes its MCP grant and attempts to interrupt the current provider session.

Provision the restricted definition independently with:

```sh
uv run python infra/scripts/managed_agent.py --tuning-only
```

Set the printed `MANAGED_TUNING_AGENT_ID` in the agent service environment alongside
`ANTHROPIC_API_KEY`, `MANAGED_ENVIRONMENT_ID` and `MCP_SERVER_URL`. Default provisioning
also syncs this third definition. It has no built-in sandbox or web tools, only the MCP
toolset. Deploy the API, agent and admin panel together and apply the scheduler change.
