"""Historical evidence and reproducible, temporally isolated workflow evaluations."""


def workflow_types(field):
    definitions = {
        "workflow_case": {
            "dataset": field(), "case_ref": field(), "revision": field(unique=True),
            "split": field(enum=["training", "holdout"]),
            "initial_context": field("text"), "initial_request": field("text"),
            "property_address": field("text"), "source_role": field(),
            "overview": field("text"), "outcome": field("text"),
            "source_paths": field("array<string>"), "source_documents": field("array<string>"),
            "attachment_manifest": field("array<object>"),
            "event_count": field("int", minimum=1), "parser_version": field(),
            "skills": field("array<string>"),
        },
        "workflow_event": {
            "case_id": field(), "ordinal": field("int", minimum=1),
            "occurred_at": field("datetime"), "channel": field(),
            "sender": field(), "recipient": field(), "body": field("text"),
            "raw_text": field("text"),
            "kind": field(enum=["agent_action", "external_observation"]),
            "source_document": field(), "char_start": field("int", minimum=0),
            "char_end": field("int", minimum=0), "attachments": field("array<string>"),
        },
        "workflow_transition": {
            "case_id": field(), "from_event": field(), "to_event": field(),
            "after_step": field("int", minimum=1), "target_step": field("int", minimum=2),
            "evaluable": field("bool"), "reason": field("text"),
            "rubric_version": field(),
        },
        "workflow_triplet": {
            "case_id": field(), "case_ref": field(), "dataset": field(), "split": field(enum=["training", "holdout"]),
            "start_step": field("int", minimum=1), "end_step": field("int", minimum=3),
            "event_ids": field("array<string>"), "context": field("text", embed=False),
            "text": field("text", embed=False), "next_step": field("text", embed=False),
            "next_kind": field(enum=["agent_action", "external_observation"]),
            "stage": field(), "metadata": field("array<object>"),
            "actions": field("array<text>", embed=False), "decisions": field("array<text>", embed=False),
            "insights": field("array<text>", embed=False), "tags": field("array<string>"),
            "channels": field("array<string>"), "participants": field("array<string>"),
            "skills": field("array<string>"), "extractor_version": field(),
            "metadata_provider": field("object"), "embedding_model": field(),
        },
        "workflow_evaluation": {
            "tuning_mode": field(enum=["prediction", "revision"]),
            "transition_id": field(), "case_id": field(), "run_id": field(),
            "status": field(enum=["prepared", "running", "graded", "failed"]),
            "agent_provider": field("object"), "skill_versions": field("object"),
            "context_hash": field(), "context": field("text"),
            "actual": field("text"), "expected": field("text"),
            "judge_model": field(), "judge_response_id": field(),
            "judge_usage": field("object"), "rubric_version": field(),
            "scores": field("object"), "score": field("decimal", minimum=0, maximum=100),
            "passed": field("bool"), "explanation": field("text"),
            "differences": field("array<text>"), "error": field("text"),
        },
    }
    return {
        key: {"id": key, "name": key.replace("_", " ").title(), "fields": fields,
              "version": 1, "primary": False}
        for key, fields in definitions.items()
    }
