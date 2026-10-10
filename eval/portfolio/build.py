"""Write a sizeable portfolio of linked raw sources and import instructions."""

import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path

from .catalogue import AS_OF, catalogue, person, property_record
from .io import digest, fresh_directory, write_json
from .stories import TOPICS, eml, repair


def money(pence):
    return f"{pence // 100}.{pence % 100:02}"


def build(destination, properties=120, seed=20261010):
    if not 1 <= properties <= 1000:
        raise ValueError("Choose 1–1000 properties")
    root = fresh_directory(destination)
    cat = catalogue(seed)
    source_rows = []
    relationship_rows = []
    expected = []
    variants = Counter()
    explicit = {}

    def source(path, text, *, mime="text/markdown", records=None, source_type=None, shard=None):
        target = root / "sources" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        payload = {"filename": Path(path).name, "mime": mime, "origin": "synthetic_env"}
        if records:
            payload["records"] = records
        if source_type:
            payload["source_type"] = source_type
        item = {"path": "sources/" + path, "sha256": hashlib.sha256(text.encode()).hexdigest(),
                "shard": shard, "upload": payload}
        source_rows.append(item)
        return item["path"]

    def crm(path, records, shard=None):
        for item in records:
            if item["type"] != "transaction":
                explicit[item["id"]] = item
        return source(path, json.dumps(records, indent=2) + "\n", mime="application/json", shard=shard)

    def link(source_id, target_id, relation, evidence, attributes=None, shard=None):
        relationship_rows.append({"source": source_id, "target": target_id, "relation": relation,
                                  "attributes": attributes or {}, "evidence_source": evidence, "shard": shard})

    crm("directory/agency.json", [cat["agency"]])
    crm("directory/landlords.json", cat["landlords"])
    for provider, contact in zip(cat["providers"], cat["provider_contacts"]):
        offerings = [r for r in cat["offerings"] if r["provider_id"] == provider["id"]]
        evidence = crm(f"directory/{provider['fields']['ref']}.json", [provider, contact, *offerings])
        link(provider["id"], contact["id"], "contact", evidence, {"role": "booking contact"})

    for n in range(1, properties + 1):
        prop = property_record(n, seed)
        ref = prop["fields"]["ref"]
        prefix = f"properties/{ref}"
        tenants = [person(n * 2 - 1, "tenant"), person(n * 2, "tenant")]
        owner = cat["landlords"][(n - 1) % 30]
        owner2 = cat["landlords"][n % 30]
        owners = [owner, owner2] if n % 5 == 0 else [owner]
        crm_path = crm(f"{prefix}/crm.json", [*owners, *tenants, prop], ref)
        relationships = [
            {"source": owner["id"], "target": prop["id"], "relation": "owns", "attributes": {"share_pct": 75 if n % 5 == 0 else 100}},
            {"source": cat["agency"]["id"], "target": prop["id"], "relation": "manages", "attributes": {}},
        ]
        if n % 5 == 0:
            relationships.append({"source": owner2["id"], "target": prop["id"], "relation": "owns", "attributes": {"share_pct": 25}})
        relationships += [{"source": tenant["id"], "target": prop["id"], "relation": "tenant_of",
                           "attributes": {"from": "2026-05-01", "to": "2027-04-30", "is_lead_tenant": i == 0}}
                          for i, tenant in enumerate(tenants)]
        relation_source = source(f"{prefix}/relationships.md", "# Supplied CRM relationships\n\n"
                                 + json.dumps(relationships, indent=2) + "\n", shard=ref)
        for row in relationships:
            link(**{key + "_id" if key in {"source", "target"} else key: value for key, value in row.items()},
                 evidence=relation_source, shard=ref)
        rent = prop["fields"]["rent_amount_minor"]
        source(f"{prefix}/tenancy.txt", f"Property: {ref}\nTenant: {tenants[0]['id']}\n"
               f"Rent: £{money(rent)}\nFrequency: monthly\nDue day: 1\nDeposit: £{money(rent)}\n"
               "Start date: 2026-05-01\nEnd date: 2027-04-30\n",
               mime="text/plain", source_type="tenancy_agreement", shard=ref)
        source(f"{prefix}/management-policy.md", f"# Management instruction for {ref}\n"
               f"Landlord: {owner['name']} ({owner['fields']['emails'][0]}).\n"
               "Diagnostic attendance is allowed up to £100 including tax. Replacement parts require specific landlord approval.\n"
               "Confirm scope, gross price and current tenant access consent. Possession of keys does not grant access.\n"
               "Escalate unresolved safety concerns to the supplied duty contact; never claim a completed visit without evidence.\n"
               "Duty contact: operations@portfolio.example.test (synthetic only).\n", shard=ref)
        charges = []
        bank = []
        received = 0
        for month in range(5, 11):
            charges.append({"type": "transaction", "name": f"Rent due {ref} 2026-{month:02}",
                            "property_id": prop["id"], "fields": {
                                "ref": f"DUE-{ref}-2026{month:02}", "external_ref": f"DUE-{ref}-2026{month:02}",
                                "kind": "charge", "category": "rent_due", "amount_minor": rent, "currency": "GBP",
                                "effective_date": f"2026-{month:02}-01", "status": "expected",
                                "description": f"Monthly rent charge for {ref}", "confidence": 1.0}})
            paid = 0 if n % 10 == 0 and month == 10 else rent // 2 if n % 7 == 0 and month == 10 else rent
            if paid:
                received += paid
                bank.append([f"2026-{month:02}-02", money(paid), f"BANK-{ref}-2026{month:02}", tenants[0]["name"], ref, "Rent payment"])
        charges.append({"type": "transaction", "name": f"Deposit received {ref}", "property_id": prop["id"],
                        "fields": {"ref": f"DEP-{ref}", "external_ref": f"DEP-{ref}", "kind": "payment",
                                   "category": "deposit_received", "amount_minor": rent, "currency": "GBP",
                                   "effective_date": "2026-05-01", "status": "cleared", "confidence": 1.0,
                                   "description": f"Opening deposit receipt for {ref}"}})
        crm(f"{prefix}/opening-ledger.json", charges, ref)
        expenses = 0
        repair_rows = []
        for slot in range(4):
            index = (n - 1) * 4 + slot
            trade_index = [3, 1, 0, 4, 5, 2, 7, 11][index % len(TOPICS)]
            provider = cat["providers"][trade_index + 12 * ((index // 8) % 3)]
            story = repair(n, slot, prop, tenants[slot % 2], provider)
            variants[story["variant"]] += 1
            ticket, quote = story["ticket"], story["quote"]
            path = f"{prefix}/repairs/{ticket['fields']['ref']}"
            ticket_source = crm(f"{path}/ticket-and-quote.json", [ticket, quote], ref)
            source(f"{path}/intake.eml", story["intake"], mime="message/rfc822", shard=ref)
            source(f"{path}/update.eml", story["update"], mime="message/rfc822", shard=ref)
            source(f"{path}/call.txt", story["call_text"], mime="text/plain", records=[story["call"]], shard=ref)
            explicit[story["call"]["id"]] = story["call"]
            source(f"{path}/quote.md", f"# Quote {quote['fields']['ref']}\nProperty: {ref}\n"
                   f"Provider: {provider['name']}\nScope: {quote['fields']['scope']}\n"
                   f"Total gross: £{money(story['amount_minor'])}\nValid until: {quote['fields']['valid_until']}\n"
                   f"Exclusions: {quote['fields']['exclusions']}\nNo appointment is implied by this quotation.\n", shard=ref)
            invoice = None
            if story["variant"] in {"completed_paid", "invoice_disputed"}:
                amount = story["amount_minor"] + (5000 if story["variant"] == "invoice_disputed" else 0)
                invoice = f"INV-{ticket['fields']['ref']}"
                source(f"{path}/invoice.txt", f"Invoice: {invoice}\nDate: 2026-10-09\nTotal: £{money(amount)}\n"
                       f"Property: {ref}\nProvider id: {provider['id']}\nTicket: {ticket['id']}\n"
                       f"Description: {ticket['fields']['title']}\n", mime="text/plain", source_type="invoice", shard=ref)
                if story["variant"] == "completed_paid":
                    expenses += amount
                    bank.append(["2026-10-09", "-" + money(amount), invoice, provider["name"], ref, "Completed repair payment"])
            if story["variant"] == "completed_paid":
                source(f"{path}/landlord-approval.eml", eml(f"{ticket['fields']['ref']}-approval",
                       owner["fields"]["emails"][0], "operations@portfolio.example.test",
                       f"Approval {quote['fields']['ref']}",
                       f"I approve {quote['fields']['ref']} for {ref}: {quote['fields']['scope']}, "
                       f"£{money(story['amount_minor'])} including tax, for the agreed 9 October visit. "
                       "This approval covers the quoted scope only.", "Thu, 08 Oct 2026 10:00:00 +0000"),
                       mime="message/rfc822", shard=ref)
                link(ticket["id"], provider["id"], "assigned_to", ticket_source, shard=ref)
            repair_rows.append({"ticket_id": ticket["id"], "quote_id": quote["id"], "provider_id": provider["id"],
                                "variant": story["variant"], "invoice_ref": invoice})
        csv_text = io.StringIO()
        writer = csv.writer(csv_text, lineterminator="\n")
        writer.writerow(["Date", "Amount", "Reference", "Counterparty", "Property Ref", "Description"])
        writer.writerows(bank)
        source(f"{prefix}/bank.csv", csv_text.getvalue(), mime="text/csv", source_type="bank_statement", shard=ref)
        unknown = n % 12 == 0
        if unknown:
            source(f"{prefix}/unallocated.ofx", f"<OFX><BANKTRANLIST><STMTTRN><DTPOSTED>20261009<TRNAMT>37.50<FITID>UNIDENTIFIED-{n:06}<NAME>Unknown sender</STMTTRN></BANKTRANLIST></OFX>\n",
                   mime="application/x-ofx", source_type="bank_statement", shard=ref)
        expected.append({"property_id": prop["id"], "property_ref": ref, "crm_source": crm_path,
                         "tenant_ids": [r["id"] for r in tenants], "owners": [r for r in relationships if r["relation"] == "owns"],
                         "repairs": repair_rows, "unallocated_count": int(unknown),
                         "balances": {"tenant_balance_minor": rent * 6 - received,
                                      "landlord_balance_minor": received - received // 10 - expenses,
                                      "deposit_held_minor": rent}})
    # Small per-property indexes keep individual files inspectable at large scales.
    for ref in [None, *[row["property_ref"] for row in expected]]:
        name = ref or "directory"
        write_json(root / "import" / f"{name}.json", {
            "sources": [s for s in source_rows if s["shard"] == ref],
            "relationships": [r for r in relationship_rows if r["shard"] == ref]})
    for row in expected:
        write_json(root / "evaluator-only" / f"{row['property_ref']}.json", row)
    counts = Counter(item["type"] for item in explicit.values())
    manifest = {"kind": "synthetic_property_portfolio", "schema_version": 1, "seed": seed,
                "as_of": AS_OF, "properties": properties, "source_files": len(source_rows),
                "explicit_records_by_type": dict(sorted(counts.items())), "repair_variants": dict(variants),
                "index_files": ["import/directory.json", *[f"import/{r['property_ref']}.json" for r in expected]],
                "sources_sha256": digest(source_rows), "execution_performed": False,
                "mode": "Historical portfolio snapshot; includes known outcomes, not a blind agent benchmark."}
    write_json(root / "manifest.json", manifest)
    return manifest
