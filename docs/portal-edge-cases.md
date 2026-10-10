# Workflow edge-case review

Reviewed against the supplied “Property Management Workflows”, dated 10 October
2026. This is an implementation review of its workflow requirements, not a
verification of the document's legal statements or a claim of complete automation.

| Scenario / source | Current behaviour and evidence |
| --- | --- |
| Danger hidden in an unrelated message; unknown contact (TT2, TT4, MT1, SF3) | Canonical ticket text and linked messages are scanned before human-control decisions. Danger raises Emergency review even without a matched contact. New smoke/fire, sparks, flooding, ceiling, security and CO-alarm signals are included. This is conservative text routing, not a separate clinical/safety checker or image analysis. |
| Vulnerable occupant (MT1, SF3–4) | Vulnerability wording raises at least Urgent and human review. It does not lower an existing Emergency. Automated callback and one-hour escalation timers remain integration work. |
| Confirmed emergency with no form, photos, quote or spend authority (MT3, MT6–8, LT4) | Explicit manager override requires observed-danger evidence, activates make-safe and takes over. Make-safe progress bypasses ordinary spend approval. It is available during global pause. No provider call is implied by a recorded status. |
| Suspected danger, insufficient confirmation or unanswered callback (MT2, MT6) | An automatic danger flag cannot authorise spend or autonomous dispatch. A manager must review; uncertainty is not treated as resolution. A manager can explicitly rule out the emergency with evidence; the repair stays urgent. Automated retries and external alerts are not implemented. |
| Made safe is not fixed (MT6–7, MT12–13) | Evidence-backed Made safe returns to urgent triage. Approval and tenant-fix confirmation are reset; normal spend and closure guards apply again. |
| Old danger text persists; new danger arrives after resolution (TT3–4, SF3) | The reviewed-source fingerprint prevents old evidence repeatedly reopening an emergency. Changed source evidence triggers a new review, even if the previous repair was closed. |
| Lower urgency, reopen, hand back or stale writes during emergency (SF4–6) | Ordinary downgrade/reopen and AI hand-back cannot bypass emergency review. Version checks reject stale commands. Activation and resolution are recorded in the durable timeline and event stream. |
| Bank-detail fraud, unlawful requests and tenant privacy (LT1, LT5, SF6–7) | Emergency override preserves human-only/fraud flags. Existing tenant reply screening and shared-view field allow-lists remain. A free-text reason is not independent bank verification; full identity and named-staff roles remain future work. |
| Contractor qualification, no acceptance in 15 minutes/one hour (MT6, MT9) | The override does not select or dispatch contractors. Qualification/insurance checks, acceptance races, scheduled retries and on-call delivery acknowledgements still need provider integration. A manager must handle them now. |
| Tenant has not confirmed repair (MT12–13) | Repair closure requires tenant confirmation. This does not yet enforce invoice payment release or delivery of both generated reports; those remain separate integration work. |
| Viewing consent, notice and competing bookings (LV7) | Existing viewing rules revalidate at confirmation. The repair emergency override does not change viewing notice, consent or compliance checks. |
| Other workflow breadth (TT/LT/LV/AC/TP/LP) | Multi-channel identity, translation, attachments, deduplication, automated chasing, accounting approvals, recurring access windows, applications and full self-service remain as scoped in portal.md. |

Regression tests in `tests/test_portal.py` exercise activation during pause,
missing evidence, stale writes, over-limit make-safe, guarded exit, restoration
of ordinary spend checks, source-evidence resolution, new danger on closed work,
and preservation of fraud/human-control boundaries. Existing tests cover tenant
privacy, viewing races, shared-view redaction and duplicate delivery protection.
