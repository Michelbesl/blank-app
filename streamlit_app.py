import streamlit as st
from datetime import datetime

try:
    from fpdf import FPDF
    fpdf_available = True
except ImportError:
    fpdf_available = False

st.set_page_config(page_title="Renewal Calculator", page_icon="📊")

st.markdown(
    """
    <style>
    .stButton > button {
        background-color: #007BFF;
        color: white;
        border-color: #007BFF;
    }
    .stButton > button:hover {
        background-color: #0056b3;
        border-color: #0056b3;
        color: white;
    }
    .stButton > button:focus {
        box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.5);
    }
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #007BFF !important;
        color: white !important;
        border-color: #007BFF !important;
    }
    div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #0056b3 !important;
        border-color: #0056b3 !important;
        color: white !important;
    }
    .sticky-summary {
        position: sticky;
        top: 0.1rem;
    }
    .summary-card {
        border: 1px solid #d9e2ec;
        border-radius: 0.75rem;
        padding: 0.85rem 0.95rem;
        background: #fbfdff;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.06);
        margin-top: 0;
    }
    .sticky-summary div[data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid #d9e2ec;
        border-radius: 0.75rem;
        background: #fbfdff;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.06);
    }
    .sticky-summary div[data-testid="stVerticalBlockBorderWrapper"] > div {
        padding: 0.75rem 0.85rem;
    }
    .summary-label {
        font-size: 0.84rem;
        color: #5f6b7a;
        margin-bottom: 0.08rem;
    }
    .summary-value {
        font-weight: 650;
        line-height: 1.1;
        margin-bottom: 0.56rem;
        white-space: nowrap;
    }
    .summary-net {
        color: #0d5bd7;
        font-size: 1.5rem;
    }
    .summary-gross {
        color: #334155;
        font-size: 1.5rem;
    }
    .summary-discount {
        font-size: 1.5rem;
    }
    .summary-discount-low {
        color: #2e7d32;
    }
    .summary-discount-mid {
        color: #ef6c00;
    }
    .summary-discount-high {
        color: #c62828;
    }
    .summary-items {
        color: #1f2d3d;
        font-size: 1.9rem;
    }
    .line-item-header {
        font-size: 0.9rem;
        font-weight: 650;
        margin-bottom: 0.18rem;
        white-space: nowrap;
    }
    .line-item-row {
        border-bottom: 1px solid #e8edf3;
        padding: 0.12rem 0;
        transition: background-color 120ms ease-in-out;
    }
    .line-item-row:hover {
        background-color: #f6f9fc;
    }
    .line-item-name {
        font-weight: 700;
        font-size: 1.02rem;
        line-height: 1.2;
        margin-top: 0.08rem;
        white-space: normal;
        word-break: normal;
        overflow-wrap: normal;
    }
    .line-total-cell {
        font-weight: 700;
        margin-top: 0;
        min-height: 2.35rem;
        display: flex;
        align-items: center;
        justify-content: flex-end;
        white-space: nowrap;
        text-align: right;
    }
    .line-total-cell .label {
        color: #5f6b7a;
        font-size: 0.72rem;
    }
    .line-total-cell .value {
        font-size: 1.16rem;
        font-weight: 700;
        color: #1f2d3d;
    }
    .line-item-row div[data-testid="stNumberInput"],
    .line-item-row div[data-testid="stSelectbox"],
    .line-item-row div[data-testid="stButton"] {
        margin-bottom: 0;
        margin-top: 0;
    }
    .line-item-row [data-testid="stNumberInput"] label,
    .line-item-row [data-testid="stSelectbox"] label {
        margin-bottom: 0;
    }
    div[data-testid="stNumberInput"] input {
        text-align: right;
        min-height: 2.35rem;
    }
    div[data-testid="stSelectbox"] div[data-baseweb="select"] {
        min-height: 2.35rem;
    }
    .remove-col div[data-testid="stButton"] > button {
        min-width: 2.05rem;
        width: 2.05rem;
        height: 2.35rem;
        padding: 0;
        font-size: 1rem;
        line-height: 1.1;
    }
    .remove-col {
        min-height: 2.35rem;
        display: flex;
        align-items: center;
        justify-content: center;
        padding-top: 0;
    }
    div[data-testid="stDivider"] {
        margin: 0.85rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def format_eur(amount: float) -> str:
    formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted


def get_discount_color_class(total_discount_pct: float) -> str:
    if total_discount_pct <= 30.0:
        return "summary-discount-low"
    if total_discount_pct <= 50.0:
        return "summary-discount-mid"
    return "summary-discount-high"


def parse_decimal_input(raw_value: str, fallback: float, min_value: float = 0.0, max_value: float | None = None) -> float:
    normalized = (raw_value or "").strip().replace(" ", "").replace(",", ".")
    try:
        parsed = float(normalized)
    except ValueError:
        parsed = fallback

    if parsed < min_value:
        parsed = min_value
    if max_value is not None and parsed > max_value:
        parsed = max_value
    return parsed


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


def init_usage_state():
    if "item_usage" not in st.session_state:
        st.session_state.item_usage = {**{name: 0 for name in products}, **{name: 0 for name in addons}}
    if "combo_usage" not in st.session_state:
        st.session_state.combo_usage = {}
    if "last_license_selected" not in st.session_state:
        st.session_state.last_license_selected = None


def sort_items(item_names: list[str], item_type: str, primary_license: str | None = None) -> list[str]:
    if item_type == "License":
        return sorted(item_names, key=lambda name: (-st.session_state.item_usage.get(name, 0), name))

    if primary_license and (primary_license in products):
        def combo_score(name: str) -> tuple[int, int, str]:
            return (
                -st.session_state.combo_usage.get((primary_license, name), 0),
                -st.session_state.item_usage.get(name, 0),
                name,
            )
        return sorted(item_names, key=combo_score)

    return sorted(item_names, key=lambda name: (-st.session_state.item_usage.get(name, 0), name))


def record_usage(item_name: str, item_type: str) -> None:
    st.session_state.item_usage[item_name] = st.session_state.item_usage.get(item_name, 0) + 1
    if item_type == "License":
        st.session_state.last_license_selected = item_name
    for row in st.session_state.line_items:
        existing = row["name"]
        if existing != item_name:
            st.session_state.combo_usage[(existing, item_name)] = st.session_state.combo_usage.get((existing, item_name), 0) + 1
            st.session_state.combo_usage[(item_name, existing)] = st.session_state.combo_usage.get((item_name, existing), 0) + 1


def build_offer_email(recipient_name: str, company_name: str, items: list[dict], total_net: float, total_gross: float, total_discount_pct: float, additional_note: str, language: str = "German") -> str:
    if language == "English":
        if recipient_name:
            greeting = f"Dear {recipient_name},"
        else:
            greeting = "Dear Sir or Madam,"

        if company_name:
            target_line = f"I have prepared the following offer for {company_name}:"
        else:
            target_line = "Please find our offer below:"

        lines = [
            greeting,
            "",
            "Thank you for your interest. I am pleased to submit the following offer.",
            "",
            target_line,
            "",
        ]

        for idx, row in enumerate(items, start=1):
            item_label = get_display_name(row)
            quantity_text = f" x{row['qty']}" if row["qty"] != 1 else ""

            if row["mode"] == "Discount %":
                detail = f"{row['discount_pct']:.1f}% discount"
            else:
                detail = f"Target amount USD {format_eur(row['target_net'])}"

            line_amount = row["unit_net"] * row["qty"]
            lines.append(f"{idx}. {item_label}{quantity_text} - {detail}: USD {format_eur(line_amount)}")

        lines.extend([
            "",
            f"Net total: USD {total_net:,.2f}",
            f"Gross incl. 19% VAT: USD {total_gross:,.2f}",
            f"Total discount: {total_discount_pct:.1f}%",
            "",
        ])

        if additional_note:
            lines.extend([additional_note, ""])

        lines.extend([
            "If you would like to accept this offer, please simply reply to this email.",
            "I am happy to assist you by phone to clarify any open questions or adjust the offer further.",
            "",
            "Best regards",
            "[Your Name]",
            "[Your Company]",
        ])

        return "\n".join(lines)
    else:
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
    st.session_state.next_line_item_id = 1
elif "next_line_item_id" not in st.session_state:
    st.session_state.next_line_item_id = 1

st.subheader("Add Item")
init_usage_state()

with st.container(border=True):
    item_type = st.selectbox("Item type", ["License", "Add-on"], index=0, key="item_type")
    primary_license = st.session_state.last_license_selected if item_type == "Add-on" else None

    if item_type == "License":
        item_catalog = products
        item_names = sort_items(list(item_catalog.keys()), item_type, None)
    else:
        item_catalog = addons
        item_names = sort_items(list(item_catalog.keys()), item_type, primary_license)

    selected_item = st.selectbox(
        "Select item",
        ["Select item"] + item_names,
        key="selected_item",
        index=0,
    )

    new_mode_symbol = st.selectbox("Pricing mode", ["%", "€"], key="new_mode")
    new_mode = "Discount %" if new_mode_symbol == "%" else "Target amount"
    st.caption("Choose a license or add-on. Set discount % or target amount later in the line item row.")
    add_clicked = st.button("Add line item", type="primary", use_container_width=True)

    if add_clicked:
        if selected_item != "Select item":
            catalog_price = item_catalog[selected_item]
            st.session_state.line_items.append(
                {
                    "id": st.session_state.next_line_item_id,
                    "type": item_type,
                    "name": selected_item,
                    "price": catalog_price,
                    "qty": 1,
                    "mode": new_mode,
                    "discount_pct": 0.0,
                    "target_net": catalog_price,
                    "unit_net": catalog_price,
                }
            )
            record_usage(selected_item, item_type)
            st.session_state.next_line_item_id += 1

st.divider()

line_total_net = 0.0
vat_total = 0.0
total_discount_pct = 0.0

if st.session_state.line_items:
    heading_list_col, heading_summary_col = st.columns([3.85, 1.35], gap="small")
    with heading_list_col:
        st.subheader("Line Items")
    with heading_summary_col:
        st.subheader("Totals")

    list_col, summary_col = st.columns([3.95, 1.35], gap="small")

    with list_col:
        row_col_widths = [2.15, 1.7, 0.9, 1.45, 1.85, 1.6, 0.45]
        header_cols = st.columns(row_col_widths, gap="small")
        with header_cols[0]:
            st.markdown('<div class="line-item-header">Item</div>', unsafe_allow_html=True)
        with header_cols[1]:
            st.markdown('<div class="line-item-header" style="text-align:right;">Price</div>', unsafe_allow_html=True)
        with header_cols[2]:
            st.markdown('<div class="line-item-header" style="text-align:right;">Qty</div>', unsafe_allow_html=True)
        with header_cols[3]:
            st.markdown('<div class="line-item-header">Discount Type</div>', unsafe_allow_html=True)
        with header_cols[4]:
            st.markdown('<div class="line-item-header" style="text-align:right;">Discount Value</div>', unsafe_allow_html=True)
        with header_cols[5]:
            st.markdown('<div class="line-item-header" style="text-align:right;">Line Total</div>', unsafe_allow_html=True)
        with header_cols[6]:
            st.markdown('<div class="line-item-header" style="text-align:center;">&nbsp;</div>', unsafe_allow_html=True)

        line_total_placeholders = []
        for row in st.session_state.line_items:
            st.markdown('<div class="line-item-row">', unsafe_allow_html=True)
            cols = st.columns(row_col_widths, gap="small")
            with cols[0]:
                st.markdown(f'<div class="line-item-name">{row["name"]}</div>', unsafe_allow_html=True)
            with cols[1]:
                st.markdown("<div style='height: 0.14rem;'></div>", unsafe_allow_html=True)
                row["price"] = st.number_input(
                    "Price €",
                    min_value=0.0,
                    value=row.get("price", 0.0),
                    step=1.0,
                    format="%.2f",
                    key=f"price_{row['id']}",
                    label_visibility="collapsed",
                )
            with cols[2]:
                st.markdown("<div style='height: 0.14rem;'></div>", unsafe_allow_html=True)
                row["qty"] = st.number_input(
                    "Qty",
                    min_value=0,
                    step=1,
                    value=row["qty"],
                    key=f"qty_{row['id']}",
                    label_visibility="collapsed",
                )
            with cols[3]:
                st.markdown("<div style='height: 0.14rem;'></div>", unsafe_allow_html=True)
                mode_options = ["%", "€"]
                mode_display = "%" if row.get("mode", "Discount %") == "Discount %" else "€"
                mode_index = mode_options.index(mode_display)
                selected_mode_symbol = st.selectbox(
                    "Discount Type",
                    mode_options,
                    key=f"mode_{row['id']}",
                    index=mode_index,
                    label_visibility="collapsed",
                )
                row["mode"] = "Discount %" if selected_mode_symbol == "%" else "Target amount"
            with cols[4]:
                st.markdown("<div style='height: 0.14rem;'></div>", unsafe_allow_html=True)
                if row["mode"] == "Discount %":
                    discount_value_text = st.text_input(
                        "Discount Value",
                        value=f"{row.get('discount_pct', 0.0):.1f}",
                        key=f"discount_value_pct_{row['id']}",
                        label_visibility="collapsed",
                    )
                    row["discount_pct"] = parse_decimal_input(
                        discount_value_text,
                        fallback=row.get("discount_pct", 0.0),
                        min_value=0.0,
                        max_value=100.0,
                    )
                    row["unit_net"] = row["price"] * (1 - row["discount_pct"] / 100)
                else:
                    discount_value_text = st.text_input(
                        "Discount Value",
                        value=f"{row.get('target_net', row['price']):.2f}",
                        key=f"discount_value_target_{row['id']}",
                        label_visibility="collapsed",
                    )
                    row["target_net"] = parse_decimal_input(
                        discount_value_text,
                        fallback=row.get("target_net", row["price"]),
                        min_value=0.0,
                    )
                    if row["qty"] > 0:
                        row["unit_net"] = row["target_net"] / row["qty"]
                    else:
                        row["unit_net"] = 0.0
                    row["discount_pct"] = 0.0 if row["unit_net"] >= row["price"] else (1 - row["unit_net"] / row["price"]) * 100
            with cols[5]:
                st.markdown("<div style='height: 0.14rem;'></div>", unsafe_allow_html=True)
                line_total_placeholder = st.empty()
                line_total_placeholder.markdown(
                    f'<div class="line-total-cell"><div class="value">€{row["unit_net"] * row["qty"]:,.2f}</div></div>',
                    unsafe_allow_html=True,
                )
            with cols[6]:
                st.markdown("<div style='height: 0rem;'></div>", unsafe_allow_html=True)
                st.markdown('<div class="remove-col">', unsafe_allow_html=True)
                if st.button("×", key=f"remove_{row['id']}", help="Remove this line item"):
                    st.session_state.line_items = [item for item in st.session_state.line_items if item["id"] != row["id"]]
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            line_total_placeholders.append((row, line_total_placeholder))
            st.markdown('</div>', unsafe_allow_html=True)

        line_total_net = sum(row["unit_net"] * row["qty"] for row in st.session_state.line_items)
        original_total = sum(row["price"] * row["qty"] for row in st.session_state.line_items)

    target_total = parse_decimal_input(
        st.session_state.get("target_total_text", f"{st.session_state.get('target_total', 0.0):.2f}"),
        fallback=float(st.session_state.get("target_total", 0.0)),
        min_value=0.0,
    )
    st.session_state.target_total = target_total

    footer_left, footer_right = st.columns([3.85, 1.35], gap="small")
    with footer_left:
        st.markdown("&nbsp;", unsafe_allow_html=True)
    with footer_right:
        st.markdown("<div style='height: 1.45rem;'></div>", unsafe_allow_html=True)
        if st.button("Clear all", type="secondary", key="clear_all_bottom"):
            st.session_state.line_items = []
            st.rerun()

    if target_total > 0 and line_total_net > 0:
        scale = float(target_total) / float(line_total_net)
        for row in st.session_state.line_items:
            base_price = row["price"]
            row["unit_net"] = round(row["unit_net"] * scale, 2)
            row["discount_pct"] = 0.0 if row["unit_net"] >= base_price else (1 - row["unit_net"] / base_price) * 100
            if row.get("mode") == "Target amount" and row["qty"] > 0:
                row["target_net"] = round(row["unit_net"] * row["qty"], 2)

        line_total_net = sum(row["unit_net"] * row["qty"] for row in st.session_state.line_items)
        for row, line_total_placeholder in line_total_placeholders:
            line_total_placeholder.markdown(
                f'<div class="line-total-cell"><div class="value">€{row["unit_net"] * row["qty"]:,.2f}</div></div>',
                unsafe_allow_html=True,
            )

    vat_total = line_total_net * 1.19
    total_discount_pct = 0.0 if original_total == 0 else (1 - line_total_net / original_total) * 100
    discount_color_class = get_discount_color_class(total_discount_pct)

    with summary_col:
        st.markdown('<div class="sticky-summary">', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown('<div class="summary-label">Net total</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="summary-value summary-net" style="text-align:right;">€{line_total_net:,.2f}</div>', unsafe_allow_html=True)
            st.markdown('<div class="summary-label">Gross incl. 19% VAT</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="summary-value summary-gross" style="text-align:right;">€{vat_total:,.2f}</div>', unsafe_allow_html=True)
            st.markdown('<div class="summary-label">Total decrease</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="summary-value summary-discount {discount_color_class}" style="text-align:right;">{total_discount_pct:,.1f}%</div>',
                unsafe_allow_html=True,
            )
            target_total_text = st.text_input(
                "Target total € (optional)",
                value=f"{target_total:.2f}",
                key="target_total_text",
            )
            target_total = parse_decimal_input(
                target_total_text,
                fallback=target_total,
                min_value=0.0,
            )
            st.session_state.target_total = target_total
        st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("Add a license or add-on line item with discount to start building the quote.")

st.divider()
st.subheader("Email Generator")
email_lang = st.selectbox("Email language", ["German", "English"], key="email_language")
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
            email_lang,
        )
        st.code(email_body)
        st.download_button(
            label="Download email as text",
            data=email_body,
            file_name="offer_email.txt",
            mime="text/plain",
        )
