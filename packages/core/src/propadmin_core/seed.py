"""Coherent offline UK maintenance fixture, repeatable without duplicate records."""

import math
from pathlib import Path

from .embeddings import EmbeddingService
from .graph import add_edge, create_in_state
from .ingestion import IngestionService
from .rules import RuleService
from .store import now, publish

STARTER_SKILLS = {
    "triage-maintenance-ticket": (
        "Triage maintenance",
        "Classify urgency from tenant evidence and create a plan before action.",
    ),
    "book-contractor": (
        "Book a contractor",
        "Find a contractor by trade and coverage, confirm availability, then record a visit.",
    ),
    "tenant-call": (
        "Call a tenant",
        "Confirm identity and access needs; record promises and follow-up in the ticket.",
    ),
    "graph-conventions": (
        "Graph conventions",
        "Read canonical entities, cite evidence and write with current entity versions.",
    ),
    "emergency-response": (
        "Emergency response",
        "Confirm real danger, give safety steps, arrange a make-safe and alert staff at once.",
    ),
    "landlord-approval": (
        "Landlord approval",
        "Ask for, read and record landlord approvals and quotes without inventing authority.",
    ),
    "job-completion": (
        "Job completion",
        "Verify reported work with the tenant, route the cost and resolve or close the ticket.",
    ),
    "chasing-and-follow-up": (
        "Chasing and follow-up",
        "Decide whether to act or wait, chase on schedule and escalate the channel when ignored.",
    ),
    "escalation-and-handover": (
        "Escalation and handover",
        "Hand staff only the decisions beyond the agent's authority, with a two-minute brief.",
    ),
    "communications": (
        "Communications",
        "Email the right party with confirmed facts only, sharing details strictly as needed.",
    ),
    "planning-and-sleeping": (
        "Plan and sleep",
        "Maintain one in-progress step, preserve evidence, and wake within ten minutes.",
    ),
    "workflow-review": (
        "Review a workflow",
        "Report recurring workflow issues and propose specific improvements with evidence.",
    ),
}


def sync_repository_skills(state):
    """Keep starter workflows in step with skills/<slug>/SKILL.md on every seed.

    Graphs seeded before a skill file existed (or changed) get the skill created, or a new
    version published over one the seed itself wrote. Versions from approved proposals or
    admins are never replaced.
    """
    root = Path(__file__).resolve().parents[4] / "skills"
    for slug, (title, description) in STARTER_SKILLS.items():
        path = root / slug / "SKILL.md"
        if not path.exists():
            continue
        content, key = path.read_text(), f"skill:{slug}"
        skill = state["skills"].get(key)
        if skill and (skill["content"] == content or skill["versions"][-1].get("created_by") != "seed"):
            continue
        version = skill["current_version"] + 1 if skill else 1
        version_id = f"skill_version:{slug}-v{version}"
        if key not in state["entities"]:
            create_in_state(state, {"id": key, "type": "skill", "name": title, "description": description,
                                    "fields": {"slug": slug, "source": "custom", "status": "active"}},
                            "seed", "Repository workflow")
        if version_id not in state["entities"]:
            create_in_state(state, {"id": version_id, "type": "skill_version", "name": f"{title} · version {version}",
                                    "description": description,
                                    "fields": {"version": version, "content": content,
                                               "change_summary": "Repository SKILL.md", "created_by": "seed",
                                               "published_at": now()}}, "seed", "Repository workflow")
        for edge in list(state["edges"].values()):
            if edge["source"] == key and edge["relation"] == "current":
                del state["edges"][edge["id"]]
        add_edge(state, key, version_id, "current")
        add_edge(state, key, version_id, "has_version")
        entry = {"version": version, "content": content, "created_by": "seed",
                 "change_summary": "Repository SKILL.md", "created_at": now()}
        if skill:
            skill.update(content=content, current_version=version)
            skill["versions"].append(entry)
        else:
            state["skills"][key] = {"id": key, "slug": slug, "name": title, "description": description,
                                    "source": "custom", "status": "active", "current_version": 1,
                                    "content": content, "versions": [entry]}


def seed_demo(store):
    from .addendum_upgrade import upgrade_addendum

    store.mutate(upgrade_addendum)
    embedder = EmbeddingService()

    def seed_entities(state):
        if state.get("demo_seed_entities"):
            return
        records = [
            {
                "id": "company:ember-property",
                "type": "company",
                "name": "Ember Property Management",
                "description": "Managing agent for residential flats in east London. Coordinates repairs and tenant communication.",
                "fields": {
                    "type": "managing agent",
                    "domains": ["emberproperty.example"],
                    "emails": ["repairs@emberproperty.example"],
                    "phones": ["+442079460810"],
                    "address": "18 Commercial Street, London E1 6AN",
                    "coverage_area": "East London",
                },
            },
            {
                "id": "company:moss-plumbing",
                "type": "company",
                "name": "Moss Plumbing & Heating",
                "description": "Gas Safe heating and plumbing contractor covering Shoreditch and Hackney. Emergency boiler repairs.",
                "fields": {
                    "type": "contractor",
                    "domains": ["mossplumbing.example"],
                    "emails": ["bookings@mossplumbing.example"],
                    "phones": ["+442079460820"],
                    "trades": ["plumbing", "heating"],
                    "coverage_area": "Shoreditch, Hackney and Bethnal Green",
                },
            },
            {
                "id": "company:bright-electrical",
                "type": "company",
                "name": "Bright Electrical",
                "description": "Local electrician handling faulty sockets, lighting and emergency electrical inspections.",
                "fields": {
                    "type": "contractor",
                    "domains": ["brightelectrical.example"],
                    "trades": ["electrical"],
                    "coverage_area": "Tower Hamlets and Hackney",
                    "phones": ["+442079460830"],
                },
            },
            {
                "id": "person:aisha-khan",
                "type": "person",
                "name": "Aisha Khan",
                "description": "Tenant at Flat 3B, 24 Hoxton Street. Reports loss of hot water and can give access after 17:00.",
                "external_ids": {"crm": "TEN-031"},
                "fields": {
                    "roles": ["tenant"],
                    "emails": ["aisha.khan@example.net"],
                    "phones": ["+447700900101"],
                    "address": "Flat 3B, 24 Hoxton Street, London N1 6SH",
                    "preferred_contact": "phone",
                    "availability": "Home after 17:00 on weekdays",
                    "notes": ["Knock twice; intercom is intermittent."],
                },
            },
            {
                "id": "person:daniel-moss",
                "type": "person",
                "name": "Daniel Moss",
                "description": "Dispatcher and heating engineer at Moss Plumbing. Can arrange a boiler assessment on Tuesday.",
                "fields": {
                    "roles": ["contractor"],
                    "emails": ["daniel@mossplumbing.example"],
                    "phones": ["+447700900102"],
                    "availability": "Office 08:00–17:00, on-call for emergencies",
                },
            },
            {
                "id": "person:sophie-reed",
                "type": "person",
                "name": "Sophie Reed",
                "description": "Repairs coordinator at Ember Property Management, responsible for tenant updates and contractor bookings.",
                "fields": {
                    "roles": ["staff"],
                    "emails": ["sophie@emberproperty.example"],
                    "phones": ["+447700900103"],
                },
            },
            {
                "id": "ticket:prop-1042",
                "type": "ticket",
                "name": "PROP-1042 · No hot water in Flat 3B",
                "description": "Boiler pressure drops and there has been no hot water since last night at Flat 3B, 24 Hoxton Street. No gas smell reported.",
                "fields": {
                    "ref": "PROP-1042",
                    "title": "No hot water in Flat 3B",
                    "location_detail": "Flat 3B",
                    "category": "heating",
                    "urgency": "urgent",
                    "status": "triaged",
                    "reported_at": "2026-10-09T19:30:00+00:00",
                    "tags": ["boiler", "hot-water", "hoxton"],
                    "access_instructions": "Tenant available after 17:00; call before arrival.",
                    "notes": ["Waiting for Moss Plumbing to confirm the visit slot."],
                },
            },
            {
                "id": "ticket:prop-1036",
                "type": "ticket",
                "name": "PROP-1036 · Kitchen sink leak",
                "description": "Water leaking beneath the kitchen sink at Flat 3B, 24 Hoxton Street. Tenant has placed a bucket beneath the pipe.",
                "fields": {
                    "ref": "PROP-1036",
                    "title": "Kitchen sink leak",
                    "location_detail": "Flat 3B",
                    "category": "plumbing",
                    "urgency": "routine",
                    "status": "resolved",
                    "reported_at": "2026-09-21T10:00:00+00:00",
                    "resolved_at": "2026-09-23T14:00:00+00:00",
                    "tags": ["leak", "hoxton"],
                    "cost_actual": 95,
                    "resolution": "Moss Plumbing replaced the waste trap and tested for leaks.",
                },
            },
            {
                "id": "ticket:prop-1051",
                "type": "ticket",
                "name": "PROP-1051 · Recurring sink leak",
                "description": "The kitchen sink leak returned at Flat 3B, 24 Hoxton Street. Investigate the repair completed in September.",
                "fields": {
                    "ref": "PROP-1051",
                    "title": "Recurring kitchen sink leak",
                    "location_detail": "Flat 3B",
                    "category": "plumbing",
                    "urgency": "urgent",
                    "status": "reported",
                    "reported_at": "2026-10-10T08:30:00+00:00",
                    "tags": ["leak", "hoxton", "repeat-visit"],
                },
            },
        ]
        for index, record in enumerate(records):
            if record["id"] not in state["entities"]:
                record["layout_x"] = math.cos(index * 2.399) * (100 + index * 15)
                record["layout_y"] = math.sin(index * 2.399) * (100 + index * 15)
                create_in_state(state, record, "seed", "Synthetic environment fixture", embedder)
        for ticket in ("ticket:prop-1042", "ticket:prop-1036", "ticket:prop-1051"):
            add_edge(state, ticket, "person:aisha-khan", "reported_by")
            add_edge(state, ticket, "company:ember-property", "for")
            add_edge(state, ticket, "company:moss-plumbing", "assigned_to")
        for slug, (title, description) in STARTER_SKILLS.items():
            path = Path(__file__).resolve().parents[4] / "skills" / slug / "SKILL.md"
            content = path.read_text() if path.exists() else f"# {title}\n\n{description}\n"
            entity_id = f"skill:{slug}"
            version_id = f"skill_version:{slug}-v1"
            if entity_id not in state["entities"]:
                create_in_state(
                    state,
                    {
                        "id": entity_id,
                        "type": "skill",
                        "name": title,
                        "description": description,
                        "fields": {"slug": slug, "source": "custom", "status": "active"},
                    },
                    "seed",
                    "",
                    embedder,
                )
                create_in_state(
                    state,
                    {
                        "id": version_id,
                        "type": "skill_version",
                        "name": f"{title} · version 1",
                        "description": description,
                        "fields": {
                            "version": 1,
                            "content": content,
                            "change_summary": "Initial workflow",
                            "created_by": "seed",
                            "published_at": now(),
                        },
                    },
                    "seed",
                    "",
                    embedder,
                )
            add_edge(state, entity_id, version_id, "current")
            add_edge(state, entity_id, version_id, "has_version")
            state["skills"].setdefault(
                entity_id,
                {
                    "id": entity_id,
                    "slug": slug,
                    "name": title,
                    "description": description,
                    "source": "custom",
                    "status": "active",
                    "current_version": 1,
                    "content": content,
                    "versions": [
                        {
                            "version": 1,
                            "content": content,
                            "created_by": "seed",
                            "change_summary": "Initial workflow",
                            "created_at": now(),
                        }
                    ],
                },
            )
        for slug in ("xlsx", "pdf", "docx"):
            state["skills"].setdefault(
                f"skill:{slug}",
                {
                    "id": f"skill:{slug}",
                    "slug": slug,
                    "name": slug.upper(),
                    "description": f"Anthropic {slug} document skill",
                    "source": "anthropic",
                    "status": "active",
                    "current_version": 1,
                    "versions": [],
                    "content": "",
                    "editable": False,
                },
            )
        state["demo_seed_entities"] = True
        publish(state, "demo.seeded", {"entities": len(records), "mode": "synthetic-offline"})

    store.mutate(seed_entities)
    store.mutate(sync_repository_skills)
    ingestion = IngestionService(store)
    source = """# CRM snapshot · Ember Property Management
Aisha Khan (TEN-031), aisha.khan@example.net, +447700900101 lives at Flat 3B, 24 Hoxton Street.
Daniel Moss works at Moss Plumbing & Heating, daniel@mossplumbing.example.
Sophie Reed coordinates repairs at Ember Property Management, sophie@emberproperty.example.
PROP-1042: No hot water in Flat 3B. Boiler pressure drops; no gas smell. Urgent heating visit required.
PROP-1036: Kitchen sink leak repaired by Moss Plumbing & Heating for £95 on 23 September.
PROP-1051: Kitchen sink leak returned in Flat 3B. Please investigate the previous repair.
"""
    ingestion.ingest(
        {
            "filename": "crm-maintenance.md",
            "mime": "text/markdown",
            "origin": "synthetic_env",
            "text": source,
        }
    )
    email = """From: Aisha Khan <aisha.khan@example.net>
To: Sophie Reed <sophie@emberproperty.example>
Message-ID: <prop1042-1@example.net>
Subject: PROP-1042 - boiler and no hot water
Date: Fri, 9 Oct 2026 19:30:00 +0000
Content-Type: text/plain; charset=utf-8

Hi Sophie,
There is no hot water in Flat 3B, 24 Hoxton Street. The boiler pressure keeps dropping.
There is no gas smell. I am home after 5pm. Please ask Moss Plumbing & Heating to call before coming.
Thanks, Aisha Khan
"""
    ingestion.ingest(
        {
            "filename": "prop-1042-report.eml",
            "mime": "message/rfc822",
            "origin": "synthetic_env",
            "text": email,
        }
    )
    transcript = """Call with Daniel Moss, Moss Plumbing & Heating — PROP-1042
Sophie Reed: Aisha Khan has no hot water at Flat 3B, 24 Hoxton Street. Can you attend?
Daniel Moss: We can send an engineer Tuesday at 17:30. The initial assessment is £85.
Sophie Reed: Please call Aisha Khan before arrival on +447700900101.
Daniel Moss: I will confirm the slot by email after checking the engineer rota.
"""
    ingestion.ingest(
        {
            "filename": "contractor-call.txt",
            "mime": "text/plain",
            "origin": "synthetic_env",
            "text": transcript,
            "records": [
                {
                    "id": "call:moss-boiler-followup",
                    "type": "call",
                    "name": "Call with Daniel Moss",
                    "description": "Contractor proposes Tuesday 17:30 boiler assessment, awaiting email confirmation.",
                    "fields": {
                        "call_id": "SYN-CALL-001",
                        "provider": "synthetic_env",
                        "direction": "outbound",
                        "from_number": "+447700900103",
                        "to_number": "+447700900102",
                        "started_at": "2026-10-10T09:15:00+00:00",
                        "duration_s": 182,
                        "status": "completed",
                        "objective": "Arrange urgent boiler assessment for PROP-1042",
                        "transcript_text": transcript,
                        "transcript": [
                            {
                                "turn": 0,
                                "speaker_role": "agent",
                                "text": "Can you attend the boiler fault at Flat 3B?",
                            },
                            {
                                "turn": 1,
                                "speaker_role": "callee",
                                "text": "Tuesday at 17:30, subject to rota confirmation.",
                            },
                        ],
                        "summary": "Provisional Tuesday 17:30 visit; assessment £85.",
                        "outcome": "Awaiting contractor email confirmation",
                        "action_items": ["Confirm the slot, then update Aisha Khan."],
                    },
                }
            ],
            "facts": [
                {
                    "key": "cost_quoted",
                    "value": 85,
                    "text": "£85",
                    "start": transcript.index("£85"),
                    "end": transcript.index("£85") + 3,
                    "entity_id": "ticket:prop-1042",
                    "confidence": 1.0,
                }
            ],
        }
    )
    rules = RuleService(store)
    specs = [
        {
            "id": "rule:company-domain",
            "name": "Company domain",
            "kind": "field_match",
            "source_type": "person",
            "target_type": "company",
            "relation": "works_at",
            "params": {"source_field": "email_domain", "target_field": "domains"},
        },
        {
            "id": "rule:shared-ticket-tags",
            "name": "Shared ticket tags",
            "kind": "field_overlap",
            "source_type": "ticket",
            "target_type": "ticket",
            "relation": "related_ticket",
            "params": {"source_field": "tags", "target_field": "tags"},
        },
        {
            "id": "rule:similar-tickets",
            "name": "Similar maintenance issues",
            "kind": "similarity",
            "source_type": "ticket",
            "target_type": "ticket",
            "relation": "similar_to",
            "params": {"threshold": 0.45, "top_k": 5},
        },
    ]
    current = store.snapshot()["rules"]
    for spec in specs:
        if spec["id"] not in current:
            rules.save_rule(spec)
    from .addendum_seed import seed_addendum

    seed_addendum(store)
    return {
        "entities": len(store.snapshot()["entities"]),
        "documents": len(store.snapshot()["documents"]),
        "mode": "synthetic-offline",
    }
