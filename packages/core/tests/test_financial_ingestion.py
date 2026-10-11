"""Financial sources travel through the same chunk/resolve/evidence pipeline."""

import base64

import pytest
from propadmin_core.financial_ingestion import link_candidate_relations
from propadmin_core.graph import GraphService
from propadmin_core.ingestion import IngestionService
from propadmin_core.ledger import LedgerService
from propadmin_core.store import Store


def setup():
    store = Store()
    graph = GraphService(store)
    prop = graph.create_entity({"type": "property", "name": "Example flat", "fields": {
        "ref": "P1", "address_line1": "1 Example Street", "postcode": "E1 1AA",
        "management_fee_pct": 10,
    }})
    tenant = graph.create_entity({"type": "person", "name": "Alice Tenant", "fields": {
        "emails": ["alice@example.test"], "roles": ["tenant"],
    }})
    graph.link_entities({"source": tenant["id"], "target": prop["id"], "relation": "tenant_of"})
    return store, IngestionService(store), LedgerService(store), prop["id"]


def test_email_claim_bank_csv_promotion_preserves_ledger_history_on_reingestion():
    store, ingest, ledger, prop = setup()
    email = "From: Alice Tenant <alice@example.test>\nTo: office@example.test\nSubject: P1 rent\nDate: Thu, 1 Oct 2026 10:00:00 +0000\nMessage-ID: <rent@example.test>\nContent-Type: text/plain; charset=utf-8\n\nI've paid £950 today for P1 rent.\n"
    claim_job = ingest.ingest({"filename": "claim.eml", "mime": "message/rfc822", "text": email})
    claim = next(e for e in store.snapshot()["entities"].values() if e["type"] == "transaction")
    assert claim["fields"]["status"] == "pending"
    assert ledger.get_balances(prop)["landlord_balance_minor"] == 0
    csv = "Date,Amount,Reference,Counterparty,Property Ref\n03/10/2026,950.00,BANK-001,Alice Tenant,P1\n"
    payload = {"filename": "bank.csv", "mime": "text/csv", "content_base64": base64.b64encode(csv.encode()).decode()}
    bank_job = ingest.ingest(payload)
    assert bank_job["entities"].count(claim["id"]) == 1
    assert ledger.get_balances(prop)["landlord_balance_minor"] == 85500
    assert ingest.ingest(payload)["deduplicated"]
    original_evidence = list(store.snapshot()["entities"][claim["id"]]["evidence"])
    ingest.ingest({**payload, "extractor_version": "financial-v2"})
    tx = store.snapshot()["entities"][claim["id"]]
    assert all(item in tx["evidence"] for item in original_evidence)
    assert {item["document_id"] for item in tx["evidence"]} >= {
        claim_job["document_id"], bank_job["document_id"],
    }
    assert all(item["span"]["text"] == store.snapshot()["documents"][item["document_id"]]["text"][
        item["span"]["start"]:item["span"]["end"]] for item in tx["evidence"])
    assert ledger.get_balances(prop)["landlord_balance_minor"] == 85500
    other_csv = csv.replace("BANK-001", "BANK-002")
    ingest.ingest({"filename": "another-bank.csv", "text": other_csv})
    assert ledger.get_balances(prop)["landlord_balance_minor"] == 171000


def test_ofx_unallocated_and_invoice_charge_matches_payment_with_source_evidence():
    store, ingest, ledger, prop = setup()
    ofx = "<OFX><BANKTRANLIST><STMTTRN><DTPOSTED>20261001<TRNAMT>100.01<FITID>X1<NAME>Unknown< MEMO>Misc</STMTTRN></BANKTRANLIST></OFX>"
    job = ingest.ingest({"filename": "bank.ofx", "text": ofx})
    assert len(job["unallocated"]) == 1
    staged = ledger.unallocated()[0]
    assert staged["id"] not in store.snapshot()["entities"]
    allocated = ledger.allocate(staged["id"], prop)
    assert allocated["fields"]["amount_minor"] == 10001
    invoice = "Invoice: INV-42\nDate: 2026-10-01\nTotal: £120.00\nProperty: P1\nProvider: Example Plumber\nDescription: Boiler repair\n"
    invoice_job = ingest.ingest({"filename": "invoice.txt", "source_type": "invoice", "text": invoice})
    tx = next(store.snapshot()["entities"][key] for key in invoice_job["entities"]
              if store.snapshot()["entities"][key]["type"] == "transaction")
    assert tx["fields"]["kind"] == "charge" and tx["fields"]["status"] == "expected"
    before = ledger.get_balances(prop)["landlord_balance_minor"]
    ingest.ingest({"filename": "payments.csv", "text":
                   "Date,Amount,Reference,Counterparty,Property Ref\n2026-10-02,-120,INV-42,Example Plumber,P1\n"})
    assert ledger.get_balances(prop)["landlord_balance_minor"] == before - 12000
    assert store.snapshot()["entities"][tx["id"]]["fields"]["status"] == "reconciled"
    assert any(edge["relation"] == "settles" and edge["target"] == tx["id"]
               for edge in store.snapshot()["edges"].values())
    tenancy = "Property: P1\nRent: £975.25\nFrequency: monthly\nDue day: 5\nDeposit: £1100\nTenant: Alice Tenant\nStart date: 01/10/2026\n"
    ingest.ingest({"filename": "tenancy.txt", "source_type": "tenancy_agreement", "text": tenancy})
    assert ledger.get_property(prop)["fields"]["rent_amount_minor"] == 97525
    assert ledger.get_property(prop)["fields"]["rent_due_day"] == 5
    assert ledger.get_balances(prop)["landlord_balance_minor"] == before - 12000
    with pytest.raises(ValueError):
        ingest.ingest({"filename": "invalid.csv", "text": "Date,Amount\n2026-10-01,1.001\n"})


def pdf_bytes(text):
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 20 700 Td ({escaped}) Tj ET".encode()
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
               b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    data, offsets = b"%PDF-1.4\n", [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(data)
    data += b"xref\n0 6\n0000000000 65535 f \n"
    data += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    return data + f"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()


def test_real_pdf_statement_and_provider_price_provenance():
    store, ingest, ledger, prop = setup()
    raw = pdf_bytes("2026-10-01 +950.00 P1 Alice rent")
    job = ingest.ingest({"filename": "statement.pdf", "mime": "application/pdf",
                         "source_type": "bank_statement", "content_base64": base64.b64encode(raw).decode()})
    document = store.snapshot()["documents"][job["document_id"]]
    assert document["raw_content_base64"] and document["parser"] == "bank-pdf-text-v1"
    assert ledger.get_balances(prop)["landlord_balance_minor"] == 85500
    with pytest.raises(ValueError, match="No bank statement rows"):
        ingest.ingest({"filename": "unknown-layout.pdf", "mime": "application/pdf",
                       "source_type": "bank_statement", "content_base64": base64.b64encode(
                           pdf_bytes("Statement balance: 950.00 with no item rows")).decode()})
    provider_job = ingest.ingest({"filename": "prices.txt", "text": "Example Plumber annual boiler service £90", "records": [
        {"type": "service_provider", "name": "Example Plumber", "fields": {
            "ref": "SP1", "trading_name": "Example Plumber", "trades": ["plumbing"], "status": "approved",
        }},
        {"type": "service_offering", "name": "Annual boiler service", "provider_id": "SP1", "fields": {
            "name": "Annual boiler service", "trade": "plumbing", "price_minor": 9000,
            "pricing_model": "fixed", "price_source": "email", "last_confirmed_at": "2026-10-01",
        }},
    ]})
    snapshot = store.snapshot()
    offering = next(snapshot["entities"][key] for key in provider_job["entities"]
                    if snapshot["entities"][key]["type"] == "service_offering")
    assert offering["evidence"]
    assert any(e["relation"] == "offers" and e["target"] == offering["id"] for e in snapshot["edges"].values())

    owner = GraphService(store).create_entity({"type": "person", "name": "Joint owner", "fields": {"roles": ["landlord"]}})
    store.mutate(lambda state: link_candidate_relations(state, [], {}, [{
        "source": owner["id"], "target": prop, "relation": "owns", "attributes": {"share_pct": 40},
    }]))
    assert ledger.get_balances(owner["id"])["landlord_balance_minor"] == 34200
    provider = next(e for e in snapshot["entities"].values() if e["type"] == "service_provider")
    before = store.snapshot()
    with pytest.raises(ValueError, match="Invalid endpoint"):
        store.mutate(lambda state: link_candidate_relations(state, [], {}, [{
            "source": provider["id"], "target": prop, "relation": "owns", "attributes": {"share_pct": 20},
        }]))
    assert store.snapshot() == before


def test_provider_and_ambiguous_receipts_are_not_guessed_as_tenant_rent():
    store, ingest, ledger, prop = setup()
    provider = GraphService(store).create_entity({"type": "service_provider", "name": "Example Roofer",
                                                  "fields": {"ref": "SP-ROOF", "trading_name": "Example Roofer", "status": "approved"}})
    contractor_receipt = "Receipt: RC-1\nDate: 2026-10-01\nTotal: £75.00\nProvider: Example Roofer\nProperty: P1\nDirection: outgoing\n"
    provider_job = ingest.ingest({"filename": "contractor-receipt.txt", "source_type": "receipt",
                                 "text": contractor_receipt})
    tx = next(store.snapshot()["entities"][key] for key in provider_job["entities"]
              if store.snapshot()["entities"][key]["type"] == "transaction")
    assert tx["fields"]["category"] == "expense" and tx["fields"]["status"] == "pending"
    assert any(edge["source"] == tx["id"] and edge["target"] == provider["id"] and edge["relation"] == "paid_to"
               for edge in store.snapshot()["edges"].values())
    assert ledger.get_balances(prop)["tenant_balance_minor"] == 0
    ambiguous = "Receipt: RC-2\nDate: 2026-10-02\nTotal: £300.00\nTenant: Alice Tenant\nProperty: P1\n"
    job = ingest.ingest({"filename": "ambiguous-receipt.txt", "source_type": "remittance", "text": ambiguous})
    staged = next(entry for entry in ledger.unallocated() if entry.get("needs_classification"))
    assert job["unallocated"] == [staged["id"]]
    assert "category" not in staged["payload"]["fields"]
    assert staged["payload"]["evidence"] and staged["id"] not in store.snapshot()["entities"]
    with pytest.raises(ValueError, match="explicit category"):
        ledger.allocate(staged["id"], prop)
    classified = ledger.allocate(staged["id"], prop, category="landlord_contribution")
    ledger.promote_status(classified["id"], "cleared")
    assert ledger.get_balances(prop)["landlord_balance_minor"] == 30000
    assert ledger.get_balances(prop)["tenant_balance_minor"] == 0
    with pytest.raises(ValueError, match="direction conflicts"):
        ingest.ingest({"filename": "contradictory-receipt.txt", "source_type": "receipt", "text":
                       ambiguous + "Category: landlord_contribution\nDirection: outgoing\n"})


def test_email_header_address_owned_by_company_is_not_a_new_person():
    store, ingest, _, _ = setup()
    company = GraphService(store).create_entity({"type": "company", "name": "Example Agency", "fields": {
        "type": "managing agent", "domains": ["agency.test"], "emails": ["repairs@agency.test"],
    }})
    email = "From: Alice Tenant <alice@example.test>\nTo: repairs@agency.test\nSubject: Leak\n\nWater through the kitchen ceiling.\n"
    job = ingest.ingest({"filename": "leak.eml", "mime": "message/rfc822", "text": email})
    people = [e for e in store.snapshot()["entities"].values() if e["type"] == "person"]
    assert [e["fields"]["emails"] for e in people] == [["alice@example.test"]]
    assert company["id"] in job["entities"]
