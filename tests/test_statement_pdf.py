"""Statements retain historical figures, source files and workflow correction links."""

from io import BytesIO

from fastapi.testclient import TestClient
from propadmin_core import Store
from propadmin_core.addendum_seed import seed_skills
from propadmin_runtime.auth import issue_token
from propadmin_runtime.factory import create_app
from propadmin_runtime.statements import generate_statement, statement_bytes
from propadmin_runtime.tools_ledger import run
from pypdf import PdfReader


def test_multipage_pdf_stored_sources_and_skill_caused_reversal():
    app = create_app(store=Store(), seed=False)
    app.state.store.mutate(seed_skills)
    prop = app.state.graph.create_entity({"type": "property", "name": "Long statement flat", "fields": {
        "ref": "PDF-P1", "address_line1": "1 Statement Street", "postcode": "E1 1AA"}})
    for number in range(40):
        run(app, "statement-test", "record_transaction", {
            "property_id": prop["id"], "skill": "reconcile-ledger", "fields": {
                "ref": f"PDF-{number:02}", "kind": "charge", "category": "rent_due",
                "amount_minor": 10001, "effective_date": "2026-10-01", "status": "expected",
                "description": "Monthly rent with a long description that wraps within the table column",
            }})
    first = generate_statement(app, prop["id"], "2026-10")
    reader = PdfReader(BytesIO(statement_bytes(app, first["document_id"])))
    text = "\n".join(page.extract_text() for page in reader.pages)
    assert len(reader.pages) > 1 and "PDF-00" in text and "PDF-39" in text
    assert "£4,000.40" in text and "Pending claims" in text
    second = generate_statement(app, prop["id"], "2026-10")
    assert first["document_id"] == second["document_id"]
    doc = app.state.graph.get_document(first["document_id"])
    assert doc["mime"] == "application/pdf" and doc["chunks"] and doc["raw_content_base64"]
    tx = next(item for item in app.state.store.snapshot()["entities"].values()
              if item["type"] == "transaction" and item["fields"]["ref"] == "PDF-00")
    with TestClient(app) as client:
        path = f"/v1/documents/{first['document_id']}/download"
        assert client.get(path).status_code == 401
        client.headers["Authorization"] = "Bearer " + issue_token(app.state.settings)
        response = client.get(path)
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment" in response.headers["content-disposition"]
        reversed_tx = client.post(f"/v1/transactions/{tx['id']}/reverse", json={"reason": "Workflow used wrong rent"})
        assert reversed_tx.status_code == 201
    issues = list(app.state.store.snapshot()["issues"].values())
    assert len(issues) == 1 and issues[0]["skill_id"] == "skill:reconcile-ledger"
    assert tx["id"] in issues[0]["related_entities"]
    assert app.state.ledger.get_balances(prop["id"])["tenant_balance_minor"] == 39 * 10001
