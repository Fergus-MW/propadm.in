"""Isolated, scripted Tanner Street conversation supplied for the sample workspace."""

from copy import deepcopy

MESSAGES = [
    {
        "id": "tanner-email-1",
        "author": "Sarah Mitchell",
        "recipient": "Properly Repairs",
        "subject": "Shower broken",
        "channel": "Email",
        "at": "2026-10-10T09:12:00+01:00",
        "direction": "inbound",
        "text": "Hi,\n"
        "\n"
        "The shower in my bathroom isn't working properly. The shower head seems to be broken "
        "and water sprays everywhere except where it should. Could someone come and fix it? "
        "Thanks, Sarah Flat 4, 27 Tanner Street",
        "attachments": [],
    },
    {
        "id": "tanner-email-2",
        "author": "Properly Repairs",
        "recipient": "Sarah Mitchell",
        "subject": "Re: Shower broken (#PRO-1042)",
        "channel": "Email",
        "at": "2026-10-10T09:14:00+01:00",
        "direction": "outbound",
        "text": "Hi Sarah,\n"
        "\n"
        "Thanks for letting us know, and sorry about the shower. I've logged it as repair "
        "#PRO-1042. So we can send the right person with the right part, could you reply with:\n"
        "\n"
        "1. A close-up photo of the shower head, and one of where the hose joins the wall or "
        "mixer.\n"
        "\n"
        "2. Is the head itself cracked, or is water leaking from the hose or the connection?\n"
        "\n"
        "3. Is water getting out of the shower area onto the floor anywhere in the bathroom?\n"
        "\n"
        "4. Is anything else in the bathroom leaking or not working?\n"
        "\n"
        "5. Can you still use the shower for now?\n"
        "\n"
        "6. When are you usually home this week (for example weekday evenings after 6pm, or "
        'Saturday morning)? If water is leaking anywhere it shouldn\'t be, just reply "leak" or '
        "call us on 020 7946 0000 and we'll treat it as urgent.\n"
        "\n"
        "Thanks, Properly, for Tanner Street Lettings",
        "attachments": [],
    },
    {
        "id": "tanner-email-3",
        "author": "Sarah Mitchell",
        "recipient": "Properly Repairs",
        "subject": "Re: Shower broken (#PRO-1042)",
        "channel": "Email",
        "at": "2026-10-10T09:31:00+01:00",
        "direction": "inbound",
        "text": "Hi,\n"
        "\n"
        "Photo attached. The shower head is cracked down the side, but the shower still sort of "
        "works. Actually, while I was taking the photo I noticed water coming from under the "
        "bathroom sink. It's all over the floor now and starting to go into the hallway. Not "
        "sure what to do? Sarah",
        "attachments": ["shower_head.jpg"],
    },
    {
        "id": "tanner-email-4",
        "author": "Properly Repairs",
        "recipient": "Sarah Mitchell",
        "subject": "URGENT: leak under your sink, what to do now (#PRO-1043)",
        "channel": "Email",
        "at": "2026-10-10T09:32:00+01:00",
        "direction": "outbound",
        "text": "Hi Sarah,\n"
        "\n"
        "We're treating the leak as an emergency. We're calling you now to talk you through it, "
        "and we're booking a plumber at the same time. Please do this now:\n"
        "\n"
        "1. Turn off the water under the sink. There's a small valve on each pipe under the "
        "basin. Turn the screw slot a quarter turn so it runs across the pipe. If that doesn't "
        "stop it, turn off the main stopcock, which is in the cupboard under your kitchen sink.\n"
        "\n"
        "2. Keep away from electrics. If water is near sockets, lights or the extractor fan, "
        "don't touch them. If water is reaching them, switch off the electricity at the fuse box "
        "in the hallway cupboard, but only if you can reach it with dry hands without standing "
        "in water.\n"
        "\n"
        "3. Soak it up. Put towels on the floor and a bowl under the leak.\n"
        "\n"
        "4. Move things. Lift anything valuable or electrical off the bathroom and hallway "
        "floor.\n"
        "\n"
        "5. Take a photo of the floor and under the sink once it's safe. We'll text you the "
        "plumber's name and arrival time in the next few minutes. If anyone is hurt, or water is "
        "coming through lights or sockets, call 999. Properly",
        "attachments": [],
    },
    {
        "id": "tanner-call-A",
        "author": "Properly voice agent",
        "recipient": "Sarah Mitchell",
        "subject": "Safety callback",
        "channel": "Call transcript",
        "at": "2026-10-10T09:32:00+01:00",
        "direction": "outbound",
        "text": "Properly: Hi Sarah, it's Properly calling about the leak under your sink. Are you "
        "somewhere safe, and is the water near any sockets or lights?\n"
        "\n"
        "Sarah: No, it's just on the floor.\n"
        "\n"
        "Properly: Good. Open the cupboard under the sink. You'll see two small valves on the "
        "pipes. Turn the one on the left a quarter turn with a coin or screwdriver until the "
        "slot runs across the pipe. Tell me when it's done.\n"
        "\n"
        "Sarah: Done. It's slowing down. Okay, it's stopped.\n"
        "\n"
        "Properly: Brilliant, well done. Put some towels down and move anything off the hallway "
        "floor. A plumber is being booked right now, and I'll text you his name and arrival time "
        "in a few minutes. Is anyone else home, and will you be in for the next couple of "
        "hours?\n"
        "\n"
        "Sarah: Just me, and yes, I'm in all morning.\n"
        "\n"
        "Properly: Perfect. If it starts again or reaches anything electrical, call 999 or call "
        "us back straight away. Speak soon.",
    },
    {
        "id": "tanner-call-B",
        "author": "Properly voice agent",
        "recipient": "Tom Reid · Reid Plumbing",
        "subject": "Emergency plumber accepted · 10:30",
        "channel": "Call transcript",
        "at": "2026-10-10T09:34:00+01:00",
        "direction": "outbound",
        "text": "Properly: Hi Tom, it's Properly with an emergency job. There's a leak under a bathroom "
        "basin at Flat 4, 27 Tanner Street, SE1. Water spread to the hallway, and the tenant has "
        "now isolated it at the basin valve. How soon can you get there?\n"
        "\n"
        "Tom: I can be there by 10:30.\n"
        "\n"
        "Properly: Great, you're booked for 10:30. There's also a cracked shower head in the "
        "same bathroom. We're asking the landlord to approve replacing it on the same visit, and "
        "I'll text you a yes or no before you arrive. Full details are on their way by email.\n"
        "\n"
        "Tom: Sounds good.",
    },
    {
        "id": "tanner-email-5",
        "author": "Properly Repairs",
        "recipient": "Tom Reid · Reid Plumbing",
        "subject": "Emergency job booked · today 10:30 (#PRO-1043)",
        "channel": "Email",
        "at": "2026-10-10T09:36:00+01:00",
        "direction": "outbound",
        "text": "Hi Tom,\n"
        "\n"
        "Thanks for picking this up. Here are the details:\n"
        "\n"
        "When: today, Sat 10 Oct, arriving by 10:30\n"
        "\n"
        "Where: Flat 4, 27 Tanner Street, London SE1 3LE. Buzzer\n"
        "\n"
        "4.\n"
        "\n"
        "Tenant: Sarah Mitchell, 07700 900123, home all morning\n"
        "\n"
        "Problem: water leaking from under the bathroom basin onto the floor and into the "
        "hallway. Now isolated at the left-hand basin valve; the main stopcock is under the "
        "kitchen sink. Photos attached.\n"
        "\n"
        "Job: find and fix the leak. Check the floor, and the ceiling of the flat below if you "
        "can, for water damage. Take before and after photos.\n"
        "\n"
        "Approved up to: £180 inc VAT for call-out, labour and small parts. If it will cost "
        "more, please call us before going ahead.\n"
        "\n"
        "Possible extra: replace the cracked shower head (standard ½\" fitting). We'll text you "
        "the landlord's answer before 10:15. When you're done, reply with the cause, what you "
        "did, the parts used, photos and your invoice. Update us with one tap: [On my way] · "
        "[Arrived] · [Done]\n"
        "\n"
        "Thanks, Properly, for Tanner Street Lettings",
        "attachments": [],
    },
    {
        "id": "tanner-email-6",
        "author": "Properly Repairs",
        "recipient": "Sarah Mitchell",
        "subject": "Plumber booked · Tom arriving by 10:30 (#PRO-1043)",
        "channel": "Email",
        "at": "2026-10-10T09:37:00+01:00",
        "direction": "outbound",
        "text": "Hi Sarah,\n"
        "\n"
        "Thanks for turning the water off so quickly, that really helped. Tom Reid from Reid "
        "Plumbing will be with you by 10:30 this morning. We'll text you when he's on his way, "
        "and you can follow his progress here: [Track your repair]. Please keep the valve under "
        "the sink turned off until he arrives. About your shower: we've asked for the shower "
        "head to be replaced and hope Tom can do it on the same visit. We'll confirm shortly. If "
        "you can't be in at 10:30 after all, just reply to this email. Properly",
        "attachments": [],
    },
    {
        "id": "tanner-email-8",
        "author": "Properly · Tanner Street Lettings",
        "recipient": "James Carter · Landlord",
        "subject": "Emergency leak · under control, plumber booked",
        "channel": "Email",
        "at": "2026-10-10T09:39:00+01:00",
        "direction": "outbound",
        "text": "Dear James,\n"
        "\n"
        "There's no action needed from you on this one. This morning Sarah reported water "
        "leaking from under the bathroom basin onto the floor. We treated it as an emergency. "
        "The water was turned off at 09:35, and Tom Reid from Reid Plumbing is attending at "
        "10:30. Under the emergency terms of your management agreement, we've approved up to "
        "£180 inc VAT for the call-out and repair, which is above your usual £50 limit. After "
        "the visit we'll send you the cause, the photos and the final invoice, and let you know "
        "if anything else is needed, for example any damage to the floor or the flat below.\n"
        "\n"
        "Kind regards, Properly, for Tanner Street Lettings",
        "attachments": [],
    },
    {
        "id": "tanner-email-9",
        "author": "Properly · Tanner Street Lettings",
        "recipient": "James Carter · Landlord",
        "subject": "Approval needed · shower head replacement (£64.99)",
        "channel": "Email",
        "at": "2026-10-10T09:40:00+01:00",
        "direction": "outbound",
        "text": "Dear James,\n"
        "\n"
        "Sarah also reported that the shower head is cracked down the side and spraying water "
        "(photo attached). It's normal wear and tear, so the repair falls to the landlord. Our "
        "recommendation: replace it during today's plumber visit. That saves a second call- out "
        "(around £90).\n"
        "\n"
        'Part: chrome handheld shower head, standard ½" fitting. Checked against the photo: it '
        "fits the existing hose and holder. £24.99 [product link]\n"
        "\n"
        "Fitting: £40, done during today's visit\n"
        "\n"
        "Total: £64.99 inc VAT [Approve] · [Decline] · [Call me] If you approve by 10:15, Tom "
        "will fit it today. Otherwise we'll book a separate visit this week.\n"
        "\n"
        "Kind regards, Properly, for Tanner Street Lettings",
        "attachments": [],
    },
    {
        "id": "tanner-email-7",
        "author": "Properly",
        "recipient": "Emma Clarke · Property manager",
        "subject": "Handled, FYI · emergency leak at Tanner Street (#PRO-1043)",
        "channel": "Email",
        "at": "2026-10-10T09:41:00+01:00",
        "direction": "outbound",
        "text": "Hi Emma,\n"
        "\n"
        "Nothing needs you right now. Here's the summary.\n"
        "\n"
        "What happened: at 09:12 Sarah Mitchell (Flat 4, 27 Tanner St) reported a broken shower. "
        "While answering our questions at 09:31, she said water was leaking from under the "
        "bathroom sink and spreading into the hallway.\n"
        "\n"
        "What Properly did: 09:32: classed it as an emergency, emailed safety steps and called "
        "Sarah. Water was isolated at the basin valve by 09:35. 09:34: called the emergency "
        "plumbers on our trusted list. Tom Reid (Reid Plumbing) accepted for 10:30. 09:37: "
        "confirmed with Sarah. She's home all morning. 09:39: told the landlord. Spend is "
        "approved up to £180 under the emergency terms (his normal limit is £50).\n"
        "\n"
        "Waiting on: James Carter to approve replacing the cracked shower head for £64.99 (job "
        "#PRO-1042), sent at 09:40.\n"
        "\n"
        "Next automatic steps: if there's no reply by 10:00, Properly calls James. At 10:15 it "
        "texts Tom yes or no on the shower head. Reports go to James and Sarah after the visit. "
        "[Open job card] · [Take over] Properly",
        "attachments": [],
    },
    {
        "id": "tanner-email-10",
        "author": "James Carter",
        "recipient": "Properly",
        "subject": "Re: Approval needed · shower head replacement",
        "channel": "Email",
        "at": "2026-10-10T09:52:00+01:00",
        "direction": "inbound",
        "text": "Approved, go ahead. Thanks for sorting this so quickly. James",
        "attachments": [],
    },
    {
        "id": "tanner-text-tom",
        "author": "Properly",
        "recipient": "Tom Reid",
        "subject": "Shower replacement approved",
        "channel": "SMS",
        "at": "2026-10-10T09:53:00+01:00",
        "direction": "outbound",
        "text": "Hi Tom,\n"
        "\n"
        "the landlord has approved the shower head swap at 27 Tanner St. Please bring a standard "
        "chrome handheld head with a ½\" fitting and replace it on today's visit. Approved total "
        "is now up to £244.99 inc VAT (£180 for the leak plus £64.99 for the shower head). "
        "Thanks! (Properly, #PRO-1042)",
    },
    {
        "id": "tanner-text-sarah",
        "author": "Properly",
        "recipient": "Sarah Mitchell",
        "subject": "Shower replacement confirmed",
        "channel": "SMS",
        "at": "2026-10-10T09:53:00+01:00",
        "direction": "outbound",
        "text": "Hi Sarah,\n"
        "\n"
        "good news: Tom will also replace your shower head this morning. He's still arriving by "
        "10:30. (Properly)",
    },
]


def tanner_items():
    def event(time, action, detail, actor="Properly"):
        return dict(at=f"2026-10-10T{time}:00+01:00", actor=actor, action=action, detail=detail)

    shared = dict(
        property="Flat 4, 27 Tanner Street",
        person="Sarah Mitchell",
        role="Tenant",
        version=1,
        demo=True,
        source_id=None,
        spend_limit=50,
        contractor="Tom Reid · Reid Plumbing",
        eta="10 Oct · 10:30",
        reported_at="2026-10-10T09:12:00+01:00",
        due_at="2026-10-10T10:30:00+01:00",
        draft="",
        confidence="High",
        facts=[],
        tenant_fixed=False,
        autonomy=2,
    )
    shower = dict(
        **shared,
        id="demo-pro-1042",
        title="PRO-1042 · Cracked shower head",
        urgency="Routine",
        stage=5,
        emergency=False,
        flags=[],
        estimate=64.99,
        approved=True,
        waiting_on="Tom Reid · replacement during the 10:30 visit",
        messages=[
            deepcopy(m)
            for m in MESSAGES
            if m["id"]
            in {
                "tanner-email-1",
                "tanner-email-2",
                "tanner-email-3",
                "tanner-email-9",
                "tanner-email-10",
                "tanner-text-tom",
                "tanner-text-sarah",
            }
        ],
        related_items=[dict(id="demo-pro-1043", title="PRO-1043 · Emergency basin leak")],
        reasons=[
            "Cracked head recorded in Sarah’s report; replacement priced at £24.99 plus £40 fitting.",
            "James Carter approved £64.99 at 09:52, above the usual £50 authority.",
        ],
        handover="James approved the shower replacement at 09:52. Tom and Sarah were updated at 09:53. The routine shower remains separate from the emergency leak; both are booked for the same visit.",
        timeline=[
            event("09:12", "Repair reported", "Sarah reported the cracked shower head."),
            event("09:14", "Details requested", "Requested photos, leak checks and availability."),
            event(
                "09:31",
                "Emergency split into PRO-1043",
                "Spreading basin leak gets a separate emergency response; shower stays routine.",
            ),
            event(
                "09:40",
                "Landlord approval requested",
                "£24.99 part + £40 fitting = £64.99; usual limit £50. Reply by 10:15 to use the same visit.",
            ),
            event(
                "09:52",
                "Landlord approved £64.99",
                "Approved, go ahead. Thanks for sorting this so quickly.",
                "James Carter",
            ),
            event(
                "09:53",
                "Same-visit replacement confirmed",
                "Tom and Sarah updated by text. Combined authorised amount £244.99.",
            ),
        ],
    )
    leak = dict(
        **shared,
        id="demo-pro-1043",
        title="PRO-1043 · Emergency basin leak",
        urgency="Emergency",
        stage=3,
        emergency=True,
        flags=["Emergency"],
        estimate=180,
        approved=False,
        emergency_reason="Uncontrolled basin leak spread across the bathroom floor into the hallway.",
        waiting_on="Tom Reid · attending by 10:30; basin valve isolated",
        messages=[
            deepcopy(m)
            for m in MESSAGES
            if m["id"]
            not in {"tanner-email-1", "tanner-email-2", "tanner-email-9", "tanner-email-10"}
        ],
        related_items=[dict(id="demo-pro-1042", title="PRO-1042 · Cracked shower head")],
        reasons=[
            "Water spreading from the basin into the hallway triggered a separate emergency job.",
            "Make-safe authority £180 exceeds the usual £50 limit; landlord informed at 09:39.",
            "Sarah isolated the basin valve; contractor verification and permanent repair are still outstanding.",
        ],
        handover="Sarah isolated the basin valve at 09:35 and is home all morning. Tom accepted the 10:30 visit; backup contractors were stood down. James and Emma have been informed. Keep the leak open until the contractor attends and the tenant confirms the fix.",
        timeline=[
            event("09:31", "Emergency job opened", "Separate from routine shower repair PRO-1042."),
            event(
                "09:32",
                "Emergency spend override",
                "Authorised £180 for make-safe above the normal £50 limit; safety email and callback started.",
            ),
            event(
                "09:34",
                "Tom accepted the call-out",
                "Reid Plumbing confirmed 10:30. Backup plumbers notified that the job was taken.",
            ),
            event(
                "09:35",
                "Tenant isolated basin valve",
                "Flow stopped. Contractor attendance still required.",
            ),
            event(
                "09:37", "Visit confirmed with tenant", "Sarah home all morning; kept valve off."
            ),
            event(
                "09:39",
                "Landlord informed",
                "Emergency £180 authority explained; no approval required for make-safe.",
            ),
            event(
                "09:41", "Property manager updated", "Emma received the handover and takeover link."
            ),
            event(
                "09:53",
                "Combined visit confirmed",
                "Separate shower approval received. £180 leak + £64.99 shower = £244.99.",
            ),
        ],
    )
    return [shower, leak]
