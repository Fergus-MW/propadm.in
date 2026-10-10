"""Evidence-backed statement PDFs stored through the source-file ingestion pipeline."""

import base64
import hashlib
import json
from io import BytesIO
from xml.sax.saxutils import escape

from propadmin_core.graph import add_edge
from propadmin_core.store import publish
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

BALANCES = ("tenant_balance_minor", "landlord_balance_minor", "deposit_held_minor")


def gbp(pence):
    pence = int(pence or 0)
    sign = "-" if pence < 0 else ""
    whole, fraction = divmod(abs(pence), 100)
    return f"{sign}£{whole:,}.{fraction:02d}"


def render_statement(statement):
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    cell = ParagraphStyle("LedgerCell", parent=styles["BodyText"], fontSize=8, leading=11)
    heading = ParagraphStyle("LedgerHead", parent=cell, textColor=colors.white, fontName="Helvetica-Bold")
    opening = ParagraphStyle("LedgerOpening", parent=styles["BodyText"], keepWithNext=True)
    story = [Paragraph("Property statement", styles["Title"]),
             Paragraph(escape(statement["subject"]["name"]), styles["Heading2"]),
             Paragraph(f"Period {escape(statement['period'])} | GBP | Recorded transactions", styles["BodyText"]),
             Spacer(1, 14)]
    summary = [["Tenant arrears", "Landlord funds", "Deposit held"],
               [gbp(statement["balances"].get(key)) for key in BALANCES]]
    table = Table(summary, colWidths=[170, 170, 170])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f3f0")),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                               ("TOPPADDING", (0, 0), (-1, -1), 9)]))
    story += [table, Spacer(1, 12)]
    for ledger in statement["properties"]:
        prop = ledger["property"]
        section = [Paragraph(escape(prop["name"]), styles["Heading2"])]
        share = ledger.get("share_pct", 100)
        section.append(Paragraph(f"Ownership {share:g}% | Opening landlord funds "
                                 + gbp(ledger["opening_balances"]["landlord_balance_minor"]), opening))
        data = [[Paragraph(value, heading) for value in ["Date / reference", "Category / evidence", "Amount", "Landlord balance"]]]
        for tx in ledger["transactions"]:
            fields = tx["fields"]
            sources = sorted({item.get("document_id", "") for item in tx.get("evidence", [])
                              if isinstance(item, dict) and item.get("document_id")})
            content = escape(" / ".join([fields["category"].replace("_", " "), fields["kind"], fields["status"]]))
            if fields.get("description"):
                content += "<br/>" + escape(fields["description"][:500])
            if sources:
                content += "<br/><font color='#59665b'>" + escape(
                    "Evidence: " + ", ".join(sources)) + "</font>"
            data.append([
                Paragraph(escape(fields["effective_date"] + " / " + fields["ref"]), cell),
                Paragraph(content, cell), Paragraph(gbp(fields["amount_minor"]), cell),
                Paragraph(gbp(tx["running_balances"]["landlord_balance_minor"]), cell),
            ])
        if len(data) == 1:
            data.append([Paragraph("No transactions in period", cell), "", "", ""])
        data.append([Paragraph("Closing landlord funds: "
                               + gbp(ledger["closing_balances"]["landlord_balance_minor"]), cell), "", "", ""])
        table = Table(data, colWidths=[105, 230, 75, 100], repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#244b36")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f8f6")]),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("LINEBELOW", (0, 0), (-1, 0), .5, colors.HexColor("#244b36")),
            ("SPAN", (0, -1), (-1, -1)), ("NOSPLIT", (0, -2), (-1, -1)),
        ]))
        section += [Spacer(1, 6), table, Spacer(1, 8)]
        story += [KeepTogether(section)] if not ledger["transactions"] else section
    story.append(Paragraph("This statement records money owed, received and paid elsewhere. "
                           "It does not initiate payments. Pending claims are excluded from received funds.", styles["BodyText"]))

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#59665b"))
        canvas.drawString(42, 28, "Propadmin | Evidence-backed property ledger")
        canvas.drawRightString(A4[0] - 42, 28, f"Page {document.page}")
        canvas.restoreState()

    SimpleDocTemplate(buffer, pagesize=A4, leftMargin=42, rightMargin=42,
                      topMargin=38, bottomMargin=45, title="Propadmin property statement").build(
        story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()


def generate_statement(app, subject, period):
    data = app.state.ledger.statement(subject, period)
    # Economic content determines document identity; deterministic extraction version.
    text = f"Statement for {data['subject']['name']}\nPeriod: {period}\n"
    for key in BALANCES:
        text += f"{key}: {gbp(data['balances'][key])}\n"
    for ledger in data["properties"]:
        text += ledger["property"]["name"] + "\n"
        for tx in ledger["transactions"]:
            fields = tx["fields"]
            text += (f"{fields['ref']} {fields['effective_date']} {fields['category']} "
                     f"{fields['status']} {gbp(fields['amount_minor'])}\n")
    digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:12]
    text += f"Statement snapshot: {digest}\n"
    filename = f"statement-{period}-{digest}.pdf"
    job = app.state.ingestion.ingest({"filename": filename, "mime": "application/pdf",
                                    "text": text, "parsed": True, "source_type": "statement",
                                    "origin": "generated_statement", "extractor_version": "ledger-statement-v1"})
    pdf = render_statement(data)

    def store_pdf(state):
        document = state["documents"][job["document_id"]]
        document["raw_content_base64"] = base64.b64encode(pdf).decode()
        document["statement"] = {"subject": data["subject"]["id"], "period": period}
        for item in data["properties"]:
            add_edge(state, document["id"], item["property"]["id"], "about")
        publish(state, "statement.generated", {"document_id": document["id"], "subject": subject})

    app.state.store.mutate(store_pdf)
    return {"document_id": job["document_id"], "filename": filename, "mime": "application/pdf",
            "period": period, "balances": data["balances"],
            "download_url": f"/v1/documents/{job['document_id']}/download"}


def statement_bytes(app, document_id):
    document = app.state.store.snapshot()["documents"][document_id]
    return base64.b64decode(document["raw_content_base64"])
