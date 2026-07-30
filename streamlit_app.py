import streamlit as st
from datetime import datetime

try:
    from fpdf import FPDF
    fpdf_available = True
except ImportError:
    fpdf_available = False

st.set_page_config(page_title="Renewal Calculator", page_icon="📊")


def format_eur(amount: float) -> str:
    formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted


def truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


def get_display_name(row: dict) -> str:
    if row.get("type") == "License":
        return f"License {row['name']}"
    return row["name"]


def set_pdf_font(pdf: FPDF, size: int = 11, style: str = "") -> None:
    try:
        pdf.set_font("Arial", style, size)
    except Exception:
        pdf.set_font("Helvetica", style, size)


def draw_pdf_table(pdf: FPDF, items: list[dict], page_width: float) -> None:
    widths = [page_width * 0.50, page_width * 0.08, page_width * 0.10, page_width * 0.18, page_width * 0.14]
    headers = ["Item", "Qty", "Mode", "Discount/Target", "Line total"]
    alignments = ["L", "C", "C", "L", "R"]

    pdf.set_draw_color(180, 180, 180)
    pdf.set_fill_color(240, 240, 240)
    set_pdf_font(pdf, size=9, style="B")
    for header, width, alignment in zip(headers, widths, alignments):
        pdf.cell(width, 6, header, border=1, align=alignment, fill=True)
    pdf.ln()

    set_pdf_font(pdf, size=8)
    for row in items:
        item_text = truncate_text(get_display_name(row), 42)
        qty_text = str(row["qty"])
        mode_text = "Disc" if row["mode"] == "Discount %" else "Target"
        if row["mode"] == "Discount %":
            discount_text = f"{row['discount_pct']:.1f}%"
        else:
            discount_text = f"€{row['target_net']:,.2f}"
        total_text = f"€{row['unit_net'] * row['qty']:,.2f}"

        row_height = 6
        y_start = pdf.get_y()
        for value, width, alignment in zip([item_text, qty_text, mode_text, discount_text, total_text], widths, alignments):
            pdf.set_xy(pdf.l_margin + sum(widths[: widths.index(width)]), y_start)
            pdf.multi_cell(width, row_height, value, border=1, align=alignment)
        pdf.set_xy(pdf.l_margin, y_start + row_height)


def build_offer_email(recipient_name: str, company_name: str, items: list[dict], total_net: float, total_gross: float, total_discount_pct: float, additional_note: str) -> str:
    if recipient_name:
        greeting = f"Sehr geehrte/r {recipient_name},"
    else:
        greeting = "Sehr geehrte Damen und Herren,"

    if company_name:
        target_line = f"Für {company_name} habe ich Ihnen nachfolgend ein Angebot zusammengestellt:"
    else:
        target_line = "Nachfolgend finden Sie unser Angebot:"

    lines = [
        greeting,
        "",
        "ich danke Ihnen für Ihr Interesse und freue mich, Ihnen folgendes Angebot unterbreiten zu dürfen.",
        "",
        target_line,
        "",
    ]

    for idx, row in enumerate(items, start=1):
        item_label = get_display_name(row)
        quantity_text = f" x{row['qty']}" if row["qty"] != 1 else ""

        if row["mode"] == "Discount %":
            detail = f"{row['discount_pct']:.1f}% Nachlass"
        else:
            detail = f"Zielbetrag EUR {format_eur(row['target_net'])}"

        line_amount = row["unit_net"] * row["qty"]
        lines.append(f"{idx}. {item_label}{quantity_text} - {detail}: EUR {format_eur(line_amount)}")

    lines.extend([
        "",
        f"Netto-Gesamtsumme: EUR {total_net:,.2f}",
        f"Brutto inkl. 19% MwSt.: EUR {total_gross:,.2f}",
        f"Gesamtrabatt insgesamt: {total_discount_pct:.1f}%",
        "",
    ])

    if additional_note:
        lines.extend([additional_note, ""])

    lines.extend([
        "Wenn Sie dieses Angebot annehmen möchten, antworten Sie bitte einfach auf diese E-Mail.",
        "Gerne stehe ich Ihnen auch telefonisch zur Verfügung, um offene Fragen zu klären oder das Angebot weiter anzupassen.",
        "",
        "Mit freundlichen Grüßen",
        "[Ihr Name]",
        "[Ihr Unternehmen]",
    ])

    return "\n".join(lines)

products = {
    "Remote Access": 202.80,
    "Business": 442.80,
    "Premium": 958.80,
    "Corporate": 2002.80,
}

addons = {
    "Remote Access 3 Devices": 166.80,
    "Channel Addon": 526.80,
    "Corporate Addon Package": 634.80,
    "MDS Mobile Device Support": 298.80,
    "100 Managed Devices": 312.00,
    "500 Devices": 1248.80,
    "Remote Worker": 185.88,
}

st.title("Renewal Calculator")
st.caption("Add licenses and add-ons as line items, set a discount for each one, and view the total.")

if "line_items" not in st.session_state:
    st.session_state.line_items = []

st.subheader("Add line item")
item_type = st.selectbox("Item type", ["License", "Add-on"], index=0, key="item_type")
item_catalog = products if item_type == "License" else addons
selected_item = st.selectbox("Select item", ["Select item"] + list(item_catalog.keys()), key="selected_item")
new_mode = st.selectbox("Pricing mode", ["Discount %", "Target amount"], key="new_mode")

if new_mode == "Discount %":
    new_discount_pct = st.number_input("Discount %", min_value=0.0, max_value=100.0, value=0.0, step=1.0, key="new_discount_pct")
    new_target_net = None
else:
    new_discount_pct = 0.0
    new_target_net = st.number_input("Target amount €", min_value=0.0, value=0.0, step=1.0, format="%.2f", key="new_target_net")

col_add, col_btn = st.columns([3, 1])
with col_add:
    st.caption("Choose a license or add-on and apply a discount or target amount to that line item.")
with col_btn:
    if st.button("Add line item"):
        if selected_item != "Select item":
            price = item_catalog[selected_item]
            st.session_state.line_items.append(
                {
                    "type": item_type,
                    "name": selected_item,
                    "price": price,
                    "qty": 1,
                    "mode": new_mode,
                    "discount_pct": new_discount_pct,
                    "target_net": new_target_net if new_mode == "Target amount" else price,
                }
            )

if st.button("Clear all"):
    st.session_state.line_items = []

st.divider()
st.subheader("Line items")

line_total_net = 0.0
vat_total = 0.0

if st.session_state.line_items:
    header_cols = st.columns([2.0, 1.0, 1.0, 1.4, 1.2, 0.8])
    with header_cols[0]:
        st.markdown("**Item**")
    with header_cols[1]:
        st.markdown("**Qty**")
    with header_cols[2]:
        st.markdown("**Mode**")
    with header_cols[3]:
        st.markdown("**Discount / Target**")
    with header_cols[4]:
        st.markdown("**Line total**")
    with header_cols[5]:
        st.markdown("**Actions**")

    for idx, row in enumerate(st.session_state.line_items):
        cols = st.columns([2.0, 1.0, 1.0, 1.4, 1.2, 0.8])
        with cols[0]:
            st.write(f"{row['name']} ({row['type']})")
        with cols[1]:
            row["qty"] = st.number_input("Qty", min_value=1, step=1, value=row["qty"], key=f"qty_{idx}")
        with cols[2]:
            row["mode"] = st.selectbox("Mode", ["Discount %", "Target amount"], key=f"mode_{idx}", index=0 if row.get("mode", "Discount %") == "Discount %" else 1)
        if row["mode"] == "Discount %":
            with cols[3]:
                row["discount_pct"] = st.number_input("Discount %", min_value=0.0, max_value=100.0, value=row.get("discount_pct", 0.0), step=1.0, key=f"pct_{idx}")
                row["unit_net"] = row["price"] * (1 - row["discount_pct"] / 100)
                st.write(f"{row['discount_pct']:.1f}% → €{row['unit_net']:,.2f}")
        else:
            with cols[3]:
                row["target_net"] = st.number_input("Target amount €", min_value=0.0, value=row.get("target_net", row["price"]), step=1.0, format="%.2f", key=f"target_{idx}")
                row["unit_net"] = min(row["price"], row["target_net"])
                row["discount_pct"] = 0.0 if row["unit_net"] >= row["price"] else (1 - row["unit_net"] / row["price"]) * 100
                st.write(f"€{row['target_net']:,.2f} → {row['discount_pct']:.1f}%")
        with cols[4]:
            st.write(f"€{row['unit_net'] * row['qty']:,.2f}")
        with cols[5]:
            if st.button("Remove", key=f"remove_{idx}"):
                st.session_state.line_items.pop(idx)
                st.rerun()

    line_total_net = sum(row["unit_net"] * row["qty"] for row in st.session_state.line_items)
    original_total = sum(row["price"] * row["qty"] for row in st.session_state.line_items)
    vat_total = line_total_net * 1.19
    total_discount_pct = 0.0 if original_total == 0 else (1 - line_total_net / original_total) * 100

    st.divider()
    col1, col2, col3 = st.columns(3)
    col1.metric("Net total", f"€{line_total_net:,.2f}")
    col2.metric("Gross incl. 19% VAT", f"€{vat_total:,.2f}")
    col3.metric("Total decrease", f"{total_discount_pct:,.1f}%")
else:
    st.info("Add a license or add-on line item with discount to start building the quote.")

st.divider()
st.subheader("Email Generator")
recipient_name = st.text_input("Recipient name", value="Customer")
company_name = st.text_input("Company name")
additional_note = st.text_area("Additional note", value="")

if st.button("Generate business email"):
    if not st.session_state.line_items:
        st.warning("Add line items before generating an email.")
    else:
        email_body = build_offer_email(
            recipient_name,
            company_name,
            st.session_state.line_items,
            line_total_net,
            vat_total,
            total_discount_pct,
            additional_note,
        )
        st.code(email_body)
        st.download_button(
            label="Download email as text",
            data=email_body,
            file_name="offer_email.txt",
            mime="text/plain",
        )
