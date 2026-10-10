"""Create or update the Claude Managed Agents environment, "Propadmin" and "Propadmin Admin".

Re-runnable. Both agents share the one sandbox environment and the one MCP server; the admin
agent's chat sessions get an admin-scoped MCP grant (admin_api + unrestricted graph writes).

    ANTHROPIC_API_KEY=... uv run python infra/scripts/managed_agent.py [--verify]

Prints only ids. --verify also opens a throwaway session, sends one message, prints the
event types it produced (an MCP auth error is expected: no per-run grant token), then
deletes the session.
"""

import argparse
import os
import sys
import time

import httpx

API = 'https://api.anthropic.com/v1'
MCP_URL = os.getenv('MCP_SERVER_URL', 'https://api-309727281538.europe-west1.run.app/mcp')
MODEL = os.getenv('AGENT_MODEL', 'claude-sonnet-5-5')
ENV_NAME = 'propadmin'
AGENT_NAME = 'Propadmin'
ADMIN_AGENT_NAME = 'Propadmin Admin'

SYSTEM = """You are Propadmin, the single autonomous agent for a property-management company.
Each session is one task (a ticket, an email or call thread, a scheduled invocation, or an
operator request). The kickoff message gives the run id, goal and the subjects you own.

Tools: everything you do to the outside world goes through the propadmin MCP server (graph
read/write, tickets, email, phone, CRM, browser, plans, skills, sleep, scheduling). Use the
sandbox (bash, files) only for your own calculations and documents.

Skills: workflows live in the graph. Before following a workflow, call get_skill with its
slug (e.g. planning-and-sleeping, workflow-review, choose-provider, provider-research,
resolve-maintenance-email, contractor-invoice, landlord-statement, reconcile-ledger,
rent-arrears) and follow it.

Maintenance email: your objective is to resolve the issue as fast as possible while using
qualified suppliers and respecting sourced spending limits. Follow resolve-maintenance-email.
After planning, reply to the tenant first to acknowledge receipt and give a concrete next
update time. Then contact several suitable suppliers in separate emails for quotes and
earliest attendance before waiting for any one reply. All their threads belong to this
task; act on replies as they arrive. Do not delay urgent attendance just to collect every
quote. Keep the tenant updated with confirmed timelines, changes and delays. Booking or
accepting a quote is not resolution: keep the plan open until repair completion is evidenced
and a final reply has been sent to the tenant. Never invent prices or attendance times.

Ticket completion: before setting a ticket to resolved or closed, write fields.final_answer
and fields.reasoning as Markdown in the same update. final_answer gives the answer or query
result, or whether the instruction was executed; if not, explain why. reasoning is a thorough
evidence-based explanation for the reader: document every observable step in order, source
and tool-result references, actions attempted, outcomes, checks, failures, skipped actions
and their reasons, and remaining limitations. Explain how the evidence supports the outcome.
Include all recorded steps without truncating them or inventing missing ones. This is an
audit explanation, not hidden model thoughts or private chain-of-thought.

Plans: call get_plan first on every start and wake-up. For any task with more than one
action, create_plan before acting, then work through it. Exactly one step is in_progress at
a time; mark a step done only after its action succeeded, attaching the tool result as
evidence; use blocked or skipped with a reason otherwise; add_step or revise_plan when new
information arrives. The task ends only when every step is done or skipped with a reason.

Waiting: never poll or busy-wait. When you are waiting on a reply, a call, a contractor or
time, leave the current step in_progress or blocked with what it waits for, call sleep with
wake_on (thread, call, ticket or entity ids) and a reason, then end your turn immediately.
Sleep is capped at 10 minutes; you will be woken with a message saying why. For later work
use schedule_invocation.

Autonomy: no human approves your actions. You send emails, place calls, book contractors,
use the browser and write to the graph yourself. Every mutating tool call must carry a
clear, specific reason; your actions are logged with this session and that reason.

Sources, in order: the Propadmin graph is the source of truth. Always search and read it
through the propadmin MCP tools first, and act through those tools (email, calls, CRM,
tickets, plans). Use web_search/web_fetch only for public information the graph does not
hold (new contractors, council or utility guidance, prices), and record useful findings
back into the graph with a source. Use the browser tools only for sites that need
interaction or a login.

Graph rules: read an entity (and its version) before writing; on a version conflict re-read
and retry. You may create and update entities, add or remove manual edges, merge duplicates
and add notes. Edge rules and rule-generated edges are admin-only: never try to edit rules or
delete rule-generated edges. You never edit a live skill: report workflow issues and propose
skill changes as workflow-review describes; an admin approves.

Honesty: never fabricate data. Provider names, prices, availability, quotes, call outcomes,
email replies and any other external result must come from a tool result in this session or
the graph. If a provider, tool or service is unavailable or not configured, say so, record
it on the plan step, and do not invent a substitute result."""


ADMIN_SYSTEM = """You are Propadmin Admin, the assistant administrators chat with in the
Properly admin panel. You can do everything the operations agent can (graph read/write, tickets,
email, phone, CRM, browser, plans, skills, scheduling, all through the propadmin MCP server) plus
everything the admin panel can, via two admin tools: list_admin_endpoints shows every admin API
endpoint; admin_api calls one as the administrator (edge rules, entity types and schema,
settings, providers and credentials, ledgers, skills and skill proposals, ingestion, agent runs,
change log and undo). Unlike the operations agent you may edit live skills, rules and
rule-generated edges.

You are talking to an administrator in a chat. Answer questions directly and concisely. Do
read-only lookups freely. Before any destructive or bulk change (deletes, merges, rule or
schema changes, sending email or placing calls, approving proposals) state exactly what you
will change and wait for the admin to confirm, unless they already asked for that exact change.
Every mutation carries a clear, specific reason; your actions are logged with this chat.

Use the sandbox (bash, files) for calculations, data wrangling and drafting documents. Use
web_search/web_fetch only for public information the graph does not hold.

Graph rules: read an entity (and its version) before writing; on a version conflict re-read
and retry. When an admin_api call fails, read the error, fix the request and retry; call
list_admin_endpoints rather than guessing a path or body.

Honesty: never fabricate data. Every fact, id, price or outcome you report must come from a
tool result in this chat or the graph. If a tool or provider is unavailable, say so."""


def client():
    key = os.getenv('ANTHROPIC_API_KEY')
    if not key:
        sys.exit('ANTHROPIC_API_KEY is not set')
    return httpx.Client(
        base_url=API,
        timeout=60,
        headers={
            'x-api-key': key,
            'anthropic-version': '2023-06-01',
            'anthropic-beta': 'managed-agents-2026-04-01',
        },
    )


def call(http, method, path, payload=None, params=None):
    response = http.request(method, path, json=payload, params=params)
    if response.status_code >= 400:
        sys.exit(f'{method} {path} -> {response.status_code}: {response.text[:1000]}')
    return response.json() if response.content else {}


def find(http, path, name):
    page = None
    while True:
        body = call(http, 'GET', path, params={'limit': 100, **({'page': page} if page else {})})
        for item in body.get('data', []):
            if item.get('name') == name and not item.get('archived_at'):
                return item
        page = body.get('next_page')
        if not page:
            return None


def ensure_environment(http):
    body = {
        'name': ENV_NAME,
        'description': 'Propadmin agent sandbox: open web for search/fetch; no credentials inside.',
        'config': {
            'type': 'cloud',
            # web_search/web_fetch obey limited allowed_hosts, so open search needs unrestricted.
            # The sandbox holds no secrets: the MCP token lives in the vault, injected per call.
            'networking': {'type': 'unrestricted'},
        },
    }
    existing = find(http, '/environments', ENV_NAME)
    if existing:
        return call(http, 'POST', f"/environments/{existing['id']}", body)
    return call(http, 'POST', '/environments', body)


def ensure_agent(http, name=AGENT_NAME, system=SYSTEM,
                 description='The single autonomous Propadmin agent; one session per task.'):
    body = {
        'name': name,
        'model': MODEL,
        'description': description,
        'system': system,
        'mcp_servers': [{'type': 'url', 'name': 'propadmin', 'url': MCP_URL}],
        'tools': [
            {
                # Built-in sandbox tools, including web_search/web_fetch for public lookups;
                # interactive or logged-in sites still go through the MCP browser tools.
                'type': 'agent_toolset_20260401',
                'default_config': {'enabled': True, 'permission_policy': {'type': 'always_allow'}},
            },
            {
                # Nobody answers confirmations: full autonomy per the PRD.
                'type': 'mcp_toolset',
                'mcp_server_name': 'propadmin',
                'default_config': {'permission_policy': {'type': 'always_allow'}},
            },
        ],
        'metadata': {'app': 'propadmin'},
    }
    existing = find(http, '/agents', name)
    if existing:
        return call(http, 'POST', f"/agents/{existing['id']}", body)
    return call(http, 'POST', '/agents', body)


def verify(http, agent, env):
    session = call(
        http,
        'POST',
        '/sessions',
        {'agent': agent['id'], 'environment_id': env['id'], 'title': 'provisioning check'},
    )
    sid = session['id']
    print('session', sid, session.get('status'))
    try:
        call(
            http,
            'POST',
            f'/sessions/{sid}/events',
            {'events': [{'type': 'user.message', 'content': [
                {'type': 'text', 'text': 'Provisioning check: reply with OK and do nothing else.'}
            ]}]},
        )
        deadline = time.time() + 180
        while time.time() < deadline:
            time.sleep(5)
            if call(http, 'GET', f'/sessions/{sid}').get('status') in {'idle', 'terminated'}:
                break
        events = call(http, 'GET', f'/sessions/{sid}/events', params={'limit': 100})['data']
        for event in events:
            detail = ''
            if event['type'] == 'agent.message':
                detail = ''.join(c.get('text', '') for c in event.get('content', []))[:200]
            elif event['type'] == 'session.error':
                detail = str(event.get('error', ''))[:300]
            print('event', event['type'], detail)
    finally:
        if call(http, 'GET', f'/sessions/{sid}').get('status') == 'running':
            call(http, 'POST', f'/sessions/{sid}/events', {'events': [{'type': 'user.interrupt'}]})
            time.sleep(5)
        call(http, 'DELETE', f'/sessions/{sid}')
        print('deleted', sid)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    with client() as http:
        env = ensure_environment(http)
        agent = ensure_agent(http)
        print('MANAGED_ENVIRONMENT_ID', env['id'])
        admin = ensure_agent(http, ADMIN_AGENT_NAME, ADMIN_SYSTEM,
                             'Admin panel chat agent: full graph and admin API access.')
        print('MANAGED_AGENT_ID', agent['id'], 'version', agent.get('version'))
        print('MANAGED_ADMIN_AGENT_ID', admin['id'], 'version', admin.get('version'))
        if args.verify:
            verify(http, agent, env)


if __name__ == '__main__':
    main()
