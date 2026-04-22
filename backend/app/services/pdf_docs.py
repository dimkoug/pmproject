"""Invoice + Quote PDF rendering (#1).

Uses fpdf2 (already a dep via app/tasks.py). Shared small helpers so the
two document types share layout (header, addresses, line table, totals).
Returns bytes so the caller can serve it inline or attach it to email.
"""
from __future__ import annotations

from datetime import datetime

from fpdf import FPDF


BRAND_PRIMARY = (79, 70, 229)  # indigo — matches the UI
MUTED = (100, 116, 139)         # slate


def _safe(s: str | None) -> str:
    """fpdf2 with the bundled Helvetica core font only supports latin-1.
    Coerce Unicode punctuation (em-dashes, smart quotes, €, etc.) into
    ASCII-equivalents so renders never crash on customer-provided data.
    Embedding a TTF font would avoid this, but adds 300kb+ per PDF."""
    if not s:
        return ""
    trans = {
        "–": "-", "—": "-",   # en/em dash
        "‘": "'", "’": "'",   # smart single quotes
        "“": '"', "”": '"',   # smart double quotes
        "•": "*", "…": "...",
        " ": " ",
    }
    for k, v in trans.items():
        s = s.replace(k, v)
    return s.encode("latin-1", errors="replace").decode("latin-1")


def _fmt_money(amount: float, currency: str = "USD") -> str:
    symbol = {"USD": "$", "EUR": "EUR ", "GBP": "GBP "}.get(currency.upper(), currency.upper() + " ")
    return f"{symbol}{amount:,.2f}"


def _header(pdf: FPDF, doc_title: str, doc_number: str) -> None:
    pdf.set_fill_color(*BRAND_PRIMARY)
    pdf.rect(0, 0, 210, 28, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(12, 8)
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 10, _safe(doc_title), ln=True)
    pdf.set_x(12)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, _safe(f"#{doc_number}"), ln=True)
    pdf.set_text_color(30, 30, 30)
    pdf.ln(8)


def _two_col(pdf: FPDF, left_label: str, left_val: str, right_label: str, right_val: str) -> None:
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*MUTED)
    pdf.cell(95, 5, _safe(left_label.upper()), ln=0)
    pdf.cell(95, 5, _safe(right_label.upper()), ln=True)
    pdf.set_text_color(30, 30, 30)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(95, 6, _safe(left_val or "-"), ln=0)
    pdf.cell(95, 6, _safe(right_val or "-"), ln=True)
    pdf.ln(4)


def _lines_table(pdf: FPDF, lines: list[dict], currency: str) -> None:
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(242, 244, 248)
    pdf.set_text_color(*MUTED)
    pdf.cell(96, 7, "DESCRIPTION", 0, 0, "L", True)
    pdf.cell(20, 7, "QTY", 0, 0, "R", True)
    pdf.cell(30, 7, "UNIT", 0, 0, "R", True)
    pdf.cell(34, 7, "AMOUNT", 0, 1, "R", True)
    pdf.set_text_color(30, 30, 30)
    pdf.set_font("Helvetica", "", 10)
    for ln in lines:
        pdf.cell(96, 7, _safe((ln.get("description") or "")[:70]))
        pdf.cell(20, 7, f"{ln.get('quantity') or 0:g}", 0, 0, "R")
        pdf.cell(30, 7, _fmt_money(ln.get("unit_price") or 0.0, currency), 0, 0, "R")
        pdf.cell(34, 7, _fmt_money(ln.get("amount") or 0.0, currency), 0, 1, "R")
    pdf.ln(2)


def _totals_block(pdf: FPDF, subtotal: float, tax: float, total: float, currency: str) -> None:
    pdf.set_font("Helvetica", "", 10)
    x = 120
    for label, value in [("Subtotal", subtotal), ("Tax", tax)]:
        pdf.set_x(x)
        pdf.cell(40, 6, label, 0, 0, "R")
        pdf.cell(40, 6, _fmt_money(value, currency), 0, 1, "R")
    pdf.set_x(x)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*BRAND_PRIMARY)
    pdf.cell(40, 9, "Total", 0, 0, "R")
    pdf.cell(40, 9, _fmt_money(total, currency), 0, 1, "R")
    pdf.set_text_color(30, 30, 30)


def _footer(pdf: FPDF, note: str | None) -> None:
    if not note:
        return
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(0, 5, _safe(note))


def render_invoice_pdf(invoice: dict, lines: list[dict], customer: dict | None,
                       company: dict | None, currency: str = "USD") -> bytes:
    """Render an invoice to PDF. `invoice` keys expected: invoice_number,
    invoice_date, due_date, status, subtotal, tax_amount, total_amount, notes.
    Returns the PDF bytes."""
    pdf = FPDF()
    pdf.add_page()
    _header(pdf, "INVOICE", invoice.get("invoice_number") or "—")

    bill_to = customer.get("name") if customer else "-"
    bill_to_addr = (customer or {}).get("address") or ""
    from_name = (company or {}).get("name") or "Your Company"
    issued = invoice.get("invoice_date")
    due = invoice.get("due_date")
    issued_s = issued if isinstance(issued, str) else (issued.isoformat() if isinstance(issued, datetime) else "-")
    due_s = due if isinstance(due, str) else (due.isoformat() if isinstance(due, datetime) else "-")

    _two_col(pdf, "BILL FROM", from_name, "BILL TO", f"{bill_to}\n{bill_to_addr}".strip())
    _two_col(pdf, "ISSUE DATE", issued_s[:10], "DUE DATE", due_s[:10])
    _two_col(pdf, "STATUS", (invoice.get("status") or "-").upper(),
             "AMOUNT DUE", _fmt_money(invoice.get("total_amount") or 0.0, currency))

    _lines_table(pdf, lines, currency)
    _totals_block(pdf,
                  subtotal=invoice.get("subtotal") or sum(l.get("amount") or 0.0 for l in lines),
                  tax=invoice.get("tax_amount") or 0.0,
                  total=invoice.get("total_amount") or 0.0,
                  currency=currency)
    _footer(pdf, invoice.get("notes"))

    # fpdf2 returns str for .output() in py3; coerce to bytes for the HTTP layer.
    out = pdf.output(dest="S")
    return bytes(out) if isinstance(out, (bytearray, bytes)) else out.encode("latin-1")


def render_quote_pdf(quote: dict, lines: list[dict], customer: dict | None,
                     company: dict | None, currency: str = "USD") -> bytes:
    """Render a quote to PDF. `quote` keys expected: quote_number, valid_until,
    status, subtotal, tax_amount, total_amount, terms."""
    pdf = FPDF()
    pdf.add_page()
    _header(pdf, "QUOTE", quote.get("quote_number") or "—")

    bill_to = customer.get("name") if customer else "-"
    bill_to_addr = (customer or {}).get("address") or ""
    from_name = (company or {}).get("name") or "Your Company"
    valid = quote.get("valid_until")
    valid_s = valid if isinstance(valid, str) else (valid.isoformat() if isinstance(valid, datetime) else "-")

    _two_col(pdf, "FROM", from_name, "PREPARED FOR", f"{bill_to}\n{bill_to_addr}".strip())
    _two_col(pdf, "VALID UNTIL", valid_s[:10], "STATUS", (quote.get("status") or "-").upper())

    _lines_table(pdf, lines, currency)
    _totals_block(pdf,
                  subtotal=quote.get("subtotal") or sum(l.get("amount") or 0.0 for l in lines),
                  tax=quote.get("tax_amount") or 0.0,
                  total=quote.get("total_amount") or 0.0,
                  currency=currency)
    _footer(pdf, quote.get("terms") or quote.get("notes"))

    out = pdf.output(dest="S")
    return bytes(out) if isinstance(out, (bytearray, bytes)) else out.encode("latin-1")
