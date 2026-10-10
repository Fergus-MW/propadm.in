"""Parse financial source formats without converting money through floating point."""

import base64
import copy
import csv
import hashlib
import io
import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation


def money_minor(value):
    text = str(value).strip().replace("£", "").replace(",", "")
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid monetary amount: {value}") from exc
    pence = amount * 100
    if not amount.is_finite() or pence != pence.to_integral_value():
        raise ValueError("Money must have at most two decimal places")
    return int(pence)


def source_date(value):
    text = str(value).strip()
    if re.match(r"^\d{8}(?:\d{6})?(?:\[.*)?$", text):
        return datetime.strptime(text[:8], "%Y%m%d").date().isoformat()
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d %b %Y"):
        try:
            return datetime.strptime(text, pattern).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f"Invalid financial source date: {value}")


def transaction_candidate(row, *, confidence=1.0, status="cleared", source_type="bank_statement"):
    fields = {
        "kind": row.get("kind") or "payment",
        "category": row.get("category") or ("rent_received" if row["amount"] > 0 else "expense"),
        "amount_minor": abs(row["amount"]),
        "currency": "GBP",
        "effective_date": source_date(row["date"]),
        "status": row.get("status") or status,
        "counterparty_name": row.get("counterparty") or row.get("description") or "Unknown payer",
        "description": row.get("description") or row.get("reference") or "Imported ledger entry",
        "confidence": confidence,
    }
    for key, source in (("external_ref", "reference"), ("bank_account", "bank_account")):
        if row.get(source):
            fields[key] = row[source]
    return {
        "type": "transaction", "name": fields.get("external_ref") or fields["description"],
        "fields": fields, "property_id": row.get("property_id") or row.get("property_ref"),
        "provider_id": row.get("provider_id"), "ticket_id": row.get("ticket_id"),
        "source_type": source_type,
    }


def bank_csv(text):
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise ValueError("Bank CSV needs a header row")
    names = {name: re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
             for name in reader.fieldnames}
    candidates = []
    for number, raw in enumerate(reader, 2):
        if not any(raw.values()):
            continue
        row = {names[name]: (value or "").strip() for name, value in raw.items() if name in names}
        date = row.get("date") or row.get("effective_date") or row.get("transaction_date")
        if not date:
            raise ValueError(f"Bank CSV row {number} has no date")
        if row.get("amount_minor"):
            try:
                amount = int(row["amount_minor"])
            except ValueError as exc:
                raise ValueError(f"Bank CSV row {number}: amount_minor must be an integer") from exc
        elif row.get("amount"):
            amount = money_minor(row["amount"])
        else:
            credit = row.get("credit") or row.get("paid_in") or row.get("money_in")
            debit = row.get("debit") or row.get("paid_out") or row.get("money_out")
            if credit and debit and money_minor(credit) and money_minor(debit):
                raise ValueError(f"Bank CSV row {number} contains both a debit and credit")
            if not credit and not debit:
                raise ValueError(f"Bank CSV row {number} has no amount, debit or credit")
            amount = money_minor(credit or "0") - money_minor(debit or "0")
        if amount == 0:
            continue
        row.update(date=date, amount=amount,
                   reference=row.get("external_ref") or row.get("reference") or row.get("ref"),
                   counterparty=row.get("counterparty_name") or row.get("counterparty")
                   or row.get("payee") or row.get("payer") or row.get("name"),
                   description=row.get("description") or row.get("narrative") or row.get("details"))
        candidates.append(transaction_candidate(row))
    return candidates


def bank_ofx(text):
    def tag(block, name):
        match = re.search(rf"<{name}>\s*([^<\r\n]+)", block, re.I)
        return match.group(1).strip() if match else ""

    blocks = re.findall(r"<STMTTRN>(.*?)(?:</STMTTRN>|(?=<STMTTRN>|</BANKTRANLIST>))",
                        text, re.I | re.S)
    if not blocks:
        raise ValueError("OFX source contains no STMTTRN rows")
    results = []
    for block in blocks:
        amount = money_minor(tag(block, "TRNAMT"))
        if amount == 0:
            continue
        results.append(transaction_candidate({
            "amount": amount, "date": tag(block, "DTPOSTED"),
            "reference": tag(block, "FITID"), "counterparty": tag(block, "NAME"),
            "description": tag(block, "MEMO") or tag(block, "NAME"),
        }))
    return results


def bank_pdf_text(text):
    # Digitally-born statements: ISO/UK date, signed GBP amount, narrative.
    rows = []
    pattern = r"^\s*(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})\s+([+-]?£?[\d,]+\.\d{2})\s+(.+)$"
    for match in re.finditer(pattern, text, re.M):
        rows.append(transaction_candidate({
            "date": match[1], "amount": money_minor(match[2]),
            "description": match[3], "counterparty": match[3],
        }))
    return rows


def invoice_or_receipt(text, source_type):
    def labelled(label):
        match = re.search(rf"(?im)^\s*(?:{label})\s*[:#]\s*(.+?)\s*$", text)
        return match[1] if match else None

    amount = labelled("total|amount|amount paid|invoice total")
    date = labelled("date|invoice date|payment date")
    if not amount or not date:
        return []  # Remote extraction or explicit records can handle other layouts.
    provider = labelled("provider|supplier|contractor")
    provider_id = labelled("provider id")
    ticket_id = labelled("ticket|ticket ref")
    category = "expense" if source_type == "invoice" else labelled("category|transaction category")
    direction = (labelled("direction|payment direction") or "").casefold()
    incoming = direction in {"in", "incoming", "inbound", "received", "credit", "payment in"}
    outgoing = direction in {"out", "outgoing", "outbound", "paid", "debit", "payment out"}
    if direction and not incoming and not outgoing:
        raise ValueError("Receipt direction must explicitly identify incoming or outgoing money")
    if source_type != "invoice" and not category:
        if (provider or provider_id or ticket_id) and not incoming:
            category = "expense"
        elif not outgoing and re.search(r"(?i)\brent\b", labelled("description|scope|payment for|purpose") or ""):
            category = "rent_received"
    if category:
        from .ledger_rules import CATEGORY_RULES

        if category not in CATEGORY_RULES:
            raise ValueError("Unknown receipt transaction category")
        if source_type != "invoice" and CATEGORY_RULES[category][0] not in ("payment", ("charge", "payment")):
            raise ValueError("Receipts require a payment category, not a charge or transfer")
        payment_in = {"rent_received", "deposit_received", "landlord_contribution"}
        if source_type != "invoice" and ((incoming and category not in payment_in) or
                                         (outgoing and category in payment_in)):
            raise ValueError("Receipt direction conflicts with its category")
    row = {
        "date": date, "amount": money_minor(amount),
        "reference": labelled("invoice|invoice number|receipt|reference"),
        "description": labelled("description|scope") or text[:500],
        "counterparty": provider or labelled("payer|paid by|tenant|tenant name|paid to"),
        "property_ref": labelled("property|property ref"), "ticket_id": ticket_id,
        "provider_id": provider_id or provider, "category": category,
        "kind": "charge" if source_type == "invoice" else "payment",
    }
    candidate = transaction_candidate(row, confidence=.9, status="expected" if source_type == "invoice"
                                      else "pending", source_type=source_type)
    if category is None:
        candidate["fields"].pop("category", None)
        candidate["needs_classification"] = True
    return [candidate]


def prepare_source(payload):
    result = copy.deepcopy(payload)
    text = result.get("text")
    if result.get("content_base64"):
        try:
            raw = base64.b64decode(result["content_base64"], validate=True)
        except (ValueError, TypeError) as exc:
            raise ValueError("Invalid base64 file content") from exc
        if len(raw) > 5_000_000:
            raise ValueError("Source exceeds the 5 MB ingestion limit")
        result["raw_sha256"] = hashlib.sha256(raw).hexdigest()
        if result.get("mime") == "application/pdf" or result.get("filename", "").lower().endswith(".pdf"):
            from pypdf import PdfReader

            try:
                reader = PdfReader(io.BytesIO(raw))
                if reader.is_encrypted or len(reader.pages) > 250:
                    raise ValueError("PDF must be unencrypted and at most 250 pages")
                text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
            except Exception as exc:
                raise ValueError("PDF text extraction failed; supply parsed text for this document") from exc
            if not text.strip():
                raise ValueError("Scanned PDF has no text layer; supply OCR text with parsed=true")
            result.update(parsed=True, parser="pypdf-text-v1")
        else:
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise ValueError("Source is not UTF-8 text") from exc
    if text is not None:
        result["text"] = text
    source_type = result.get("source_type")
    filename = result.get("filename", "").lower()
    if not source_type and filename.endswith(".ofx"):
        source_type = "bank_statement"
    if not source_type and filename.endswith(".csv") and text:
        header = text.splitlines()[0].lower()
        if "date" in header and any(term in header for term in ("amount", "credit", "debit", "paid in")):
            source_type = "bank_statement"
    result["source_type"] = source_type
    if text and not any(record.get("type") == "transaction" for record in result.get("records") or []):
        records = []
        if source_type == "bank_statement":
            if filename.endswith(".ofx") or "<OFX" in text.upper():
                records = bank_ofx(text)
                result["parser"] = "bank-ofx-v1"
            elif result.get("mime") == "application/pdf" or filename.endswith(".pdf"):
                records = bank_pdf_text(text)
                if not records and not result.get("records") and os.getenv("EXTRACTION_PROVIDER", "local") == "local":
                    raise ValueError(
                        "No bank statement rows were recognised in this PDF; supply explicit transaction "
                        "records or use the configured Claude extraction provider"
                    )
                result["parser"] = "bank-pdf-text-v1"
            else:
                records = bank_csv(text)
                result["parser"] = "bank-csv-v1"
        elif source_type in {"invoice", "receipt", "remittance"}:
            records = invoice_or_receipt(text, source_type)
            result["parser"] = "financial-labelled-text-v1"
        result["records"] = (result.get("records") or []) + records
    return result
