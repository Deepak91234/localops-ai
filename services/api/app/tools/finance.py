import csv
import codecs
import io
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path


def money(amount: Decimal) -> str:
    return str(amount.quantize(Decimal("0.01")))


def analyze_invoices(path: Path, as_of: date = date(2026, 10, 10)):
    """Raw and deduplicated totals both shown; duplicate records are never silently removed."""
    raw = path.read_bytes()
    encoding = "utf-32" if raw.startswith((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)) else "utf-16" if raw.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)) else "utf-8-sig"
    with io.StringIO(raw.decode(encoding, errors="strict"), newline="") as source:
        reader = csv.DictReader(source)
        required = {"vendor", "invoice_id", "due_date", "amount", "status", "category"}
        if len(reader.fieldnames or []) != len(required) or set(reader.fieldnames or []) != required:
            raise ValueError("Invoice CSV requires exactly six unique columns: vendor, invoice_id, due_date, amount, status, category.")
        rows = list(reader)
    ids = defaultdict(list)
    overdue = []
    outstanding = Decimal("0")
    all_total = Decimal("0")
    unique_outstanding = Decimal("0")
    unique_overdue = Decimal("0")
    seen = set()
    for index, row in enumerate(rows, 2):
        if set(row) != required:
            raise ValueError("Invoice CSV columns do not match the approved schema.")
        value = Decimal(row["amount"])
        if not value.is_finite() or value < 0 or value != value.quantize(Decimal("0.01")):
            raise ValueError("Invoice amounts must be finite, non-negative amounts with at most two decimal places.")
        due = date.fromisoformat(row["due_date"])
        if row["status"] not in {"paid", "unpaid"}:
            raise ValueError("Invoice status must be paid or unpaid.")
        row["row_number"] = index
        row["overdue"] = row["status"] == "unpaid" and due < as_of
        ids[row["invoice_id"]].append(row)
        all_total += value
        if row["status"] == "unpaid":
            outstanding += value
            if row["invoice_id"] not in seen:
                unique_outstanding += value
        if row["overdue"]:
            overdue.append(row)
            if row["invoice_id"] not in seen:
                unique_overdue += value
        seen.add(row["invoice_id"])
    duplicates = [{"invoice_id": invoice_id, "count": len(group), "row_numbers": [r["row_number"] for r in group], "rows": group} for invoice_id, group in ids.items() if len(group) > 1]
    calculations = {
        "as_of": as_of.isoformat(), "currency": "USD", "row_count": len(rows),
        "total_amount": money(all_total), "outstanding_total": money(outstanding),
        "overdue_total": money(sum((Decimal(r["amount"]) for r in overdue), Decimal("0"))),
        "overdue_count": len(overdue), "duplicate_id_count": len(duplicates),
        "deduplicated_outstanding_total": money(unique_outstanding), "deduplicated_overdue_total": money(unique_overdue),
        "method": "Exact Decimal sums; unpaid and due_date < as_of; deduplicated figures retain the first CSV record per invoice_id. Inspect conflicting duplicate rows before acting.",
    }
    return {"calculations": calculations, "rows": rows, "duplicate_invoices": duplicates, "overdue_rows": overdue, "sources": [{"document": path.name, "type": "csv", "synthetic": True}], "synthetic": True}
