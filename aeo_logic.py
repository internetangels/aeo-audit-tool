from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image, PageBreak,
    ListFlowable, ListItem, KeepInFrame
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors
from datetime import datetime
from urllib.parse import urlparse
import os

def _brand_from_url(site_url: str) -> str:
    try:
        host = urlparse(site_url).netloc or site_url
        host = host.replace("www.", "")
        name = host.split(".")[0]
        return name.replace("-", " ").title() if name else "Your Business"
    except Exception:
        return "Your Business"

def _wrap(cell_flowable, maxw, maxh=1000):
    # Ensures content stays inside table cells without overflow
    return KeepInFrame(maxw=maxw, maxh=maxh, content=[cell_flowable], mode="shrink")

def generate_pdf_report(
    audit_data,
    output_path,
    logo_path=None,
    contact_email="carmine@internetangels.com.au",
    site_url="",
    avg_sale_value=500,
    baseline_conv_pct=3,
    monthly_visitors=300,
    include_sales_pages=True,
):
    # ---------- Styles ----------
    styles = getSampleStyleSheet()
    title = ParagraphStyle(name="Title", fontSize=20, leading=24, spaceAfter=14, alignment=1, textColor=colors.HexColor("#1A73E8"))
    h2 = ParagraphStyle(name="H2", fontSize=14, leading=18, spaceBefore=6, spaceAfter=8, textColor=colors.HexColor("#0B5BD3"))
    h3 = ParagraphStyle(name="H3", fontSize=12, leading=15, spaceBefore=4, spaceAfter=6, textColor=colors.black)
    body = ParagraphStyle(name="Body", fontSize=9, leading=12, spaceAfter=4)
    small = ParagraphStyle(name="Small", fontSize=9, leading=12)
    cell = ParagraphStyle(name="Cell", fontSize=9, leading=12)
    blt = ParagraphStyle(name="Bullet", fontSize=9, leading=12)

    # A4 width calc to size tables: 595.275pt page width
    left_margin = right_margin = 28
    usable_width = A4[0] - left_margin - right_margin  # ~539pt

    elements = []

    # ---------- Header ----------
    if logo_path and os.path.exists(logo_path):
        try:
            elements.append(Image(logo_path, width=380, height=56))
            elements.append(Spacer(1, 8))
        except Exception:
            pass

    elements.append(Paragraph("AI Search (AEO) Audit and Action Plan", title))
    meta = "Website: %s  •  Date: %s" % (site_url or "N/A", datetime.today().strftime("%d %b %Y"))
    elements.append(Paragraph(meta, small))
    elements.append(Spacer(1, 8))

    # ---------- Sales sections (conditional) ----------
    if include_sales_pages:
        # Lost Opportunity
        base_rate = max(0.0, float(baseline_conv_pct) / 100.0)
        current_rev = monthly_visitors * base_rate * max(0, avg_sale_value)
        uplift_mult = 4.4
        potential_rev = current_rev * uplift_mult
        lost_m = max(0.0, potential_rev - current_rev)
        lost_w = lost_m / 4.345
        lost_y = lost_m * 12.0

        elements.append(Paragraph("What It Is Costing You Today (Estimated)", h2))
        lo_rows = [
            ["Metric", "Value"],
            ["Current monthly revenue (est.)", "$%s" % (int(current_rev))],
            ["With AI optimisation (est.)", "$%s" % (int(potential_rev))],
            ["You are missing (per month)", "<b>$%s</b>" % (int(lost_m))],
            ["Per week", "$%s" % (int(lost_w))],
            ["Per year", "<b>$%s</b>" % (int(lost_y))],
        ]
        # Two columns, plenty of padding
        lo_tbl = Table(
            [[_wrap(Paragraph(r[0], cell), maxw=usable_width*0.45),
              _wrap(Paragraph(r[1], cell), maxw=usable_width*0.45)] for r in lo_rows],
            colWidths=[usable_width*0.45, usable_width*0.45]
        )
        lo_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#D93025")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 8),
            ("RIGHTPADDING", (0,0), (-1,-1), 8),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("BACKGROUND", (0,1), (-1,-1), colors.whitesmoke),
        ]))
        elements.append(lo_tbl)
        elements.append(Spacer(1, 12))

        # AI vs SEO explainer (4 fixed columns)
        elements.append(Paragraph("Why AI Search Matters (vs Traditional SEO)", h2))
        cmp_rows = [
            ["Channel", "How Results Appear", "User Behaviour", "Implication"],
            ["Google SEO", "Multiple links + ads + map pack", "Scroll & compare multiple sites", "You compete for clicks; low certainty"],
            ["AI Search (AEO)", "One answer / shortlist with explanation", "Trusts summarised answer; 1–2 clicks", "Winner-takes-most attention"],
        ]
        cwidths = [usable_width*0.17, usable_width*0.33, usable_width*0.25, usable_width*0.25]  # sums to usable_width
        cmp_tbl = Table(
            [[_wrap(Paragraph(c, cell), maxw=w) for c, w in zip(row, cwidths)] for row in cmp_rows],
            colWidths=cwidths
        )
        cmp_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0B5BD3")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 8),
            ("RIGHTPADDING", (0,0), (-1,-1), 8),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("BACKGROUND", (0,1), (-1,-1), colors.whitesmoke),
        ]))
        elements.append(cmp_tbl)
        elements.append(Spacer(1, 14))

    # ---------- Executive Summary ----------
    SCORE_MAP = {"🟢": 2, "🟡": 1, "🔴": 0}
    total = sum(SCORE_MAP.get(t[0], 0) for t in audit_data.values())
    max_total = 2 * len(audit_data) if audit_data else 1
    score_pct = int(round((total / float(max_total)) * 100))
    elements.append(Paragraph("Executive Summary", h2))
    elements.append(Paragraph("Overall AEO Readiness Score: <b>%d%%</b>" % score_pct, small))
    elements.append(Spacer(1, 6))

    strengths, weaknesses, qw = [], [], []
    for k, (icon, result, rec, why, how, qwin) in audit_data.items():
        if icon == "🟢":
            strengths.append("%s: %s" % (k, result))
        else:
            weaknesses.append("%s: %s — %s" % (k, result, rec))
            if qwin:
                qw.append(qwin)

    # Dedup quick wins
    seen, qw_unique = set(), []
    for q in qw:
        if q not in seen:
            qw_unique.append(q); seen.add(q)

    if strengths:
        elements.append(Paragraph("Strengths", h3))
        elements.append(ListFlowable([ListItem(Paragraph(s, blt)) for s in strengths[:6]], bulletType="bullet", leftIndent=10))
        elements.append(Spacer(1, 4))
    if weaknesses:
        elements.append(Paragraph("Weaknesses", h3))
        elements.append(ListFlowable([ListItem(Paragraph(w, blt)) for w in weaknesses[:6]], bulletType="bullet", leftIndent=10))
        elements.append(Spacer(1, 4))
    if qw_unique:
        elements.append(Paragraph("Quick Wins (next 7 days)", h3))
        elements.append(ListFlowable([ListItem(Paragraph(q, blt)) for q in qw_unique[:6]], bulletType="bullet", leftIndent=10))
        elements.append(Spacer(1, 10))

    # ---------- ROI Projection (sales mode only) ----------
    if include_sales_pages:
        elements.append(Paragraph("Projected ROI (Conservative Model)", h2))
        elements.append(Paragraph(
            "Inputs: Avg sale value = $%s, Baseline conversion = %s%%, Monthly visitors = %s. "
            "Uplift is estimated per fix and applied to the current baseline to illustrate order-of-magnitude gains."
            % (int(avg_sale_value), int(baseline_conv_pct), int(monthly_visitors)),
            small
        ))
        elements.append(Spacer(1, 4))

        IMPACT = {
            "Service-in-City Pages":        ("High", 0.40),
            "Testimonials & Case Studies":  ("Medium", 0.25),
            "FAQ Depth":                    ("Medium", 0.20),
            "Comparison Table":             ("Medium", 0.20),
            "AI Tone of Voice":             ("Medium", 0.15),
            "Home Page Readability":        ("Medium", 0.15),
            "Pricing Transparency":         ("Low",   0.10),
            "Local & Directory Profiles":   ("Low",   0.10),
            "Reviews Quantity & Rating":    ("Low",   0.10),
            "Press / Best Of Mentions":     ("Low",   0.10),
            "Technical Markup (Schema)":    ("Low",   0.10),
            "Mobile UX & Speed":            ("Low",   0.10),
        }

        base_conv_rate = max(0.0, float(baseline_conv_pct) / 100.0)
        base_conversions = monthly_visitors * base_conv_rate

        roi_head = ["Fix", "Priority", "Impact (est.)", "Added conv./month", "Projected $/month"]
        roi_rows = [roi_head]
        for area, (icon, _res, _rec, _why, _how, _qwin) in audit_data.items():
            pri, imp = IMPACT.get(area, ("Low", 0.05))
            if icon != "🟢":
                added_conversions = base_conversions * imp
                projected_dollars = added_conversions * max(0, avg_sale_value)
                roi_rows.append([
                    area, pri, "%d%%" % int(imp * 100),
                    "%.1f" % added_conversions, "$%s" % (int(projected_dollars))
                ])
        if len(roi_rows) == 1:
            roi_rows.append(["All Good", "—", "—", "0.0", "$0"])

        # Fixed widths + padding
        roi_cw = [usable_width*0.33, usable_width*0.12, usable_width*0.14, usable_width*0.18, usable_width*0.23]
        roi_tbl = Table(
            [[_wrap(Paragraph(str(c), cell), maxw=w) for c, w in zip(row, roi_cw)] for row in roi_rows],
            colWidths=roi_cw
        )
        roi_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1A73E8")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 8),
            ("RIGHTPADDING", (0,0), (-1,-1), 8),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("BACKGROUND", (0,1), (-1,-1), colors.whitesmoke),
        ]))
        elements.append(roi_tbl)
        elements.append(Spacer(1, 14))

    # ---------- Findings summary table (layout-fixed) ----------
    elements.append(Paragraph("Findings Summary", h2))
    fs_head = ["Audit Area", "Score", "Result", "Recommendation"]
    fs_rows = [fs_head]
    for area, (icon, result, rec, _why, _how, _qwin) in audit_data.items():
        fs_rows.append([area, icon, result, rec])

    fs_cw = [usable_width*0.24, usable_width*0.09, usable_width*0.31, usable_width*0.36]  # wider last cols
    fs_tbl = Table(
        [[_wrap(Paragraph(str(c), cell), maxw=w) for c, w in zip(row, fs_cw)] for row in fs_rows],
        colWidths=fs_cw
    )
    fs_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1A73E8")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 10),
        ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("BACKGROUND", (0,1), (-1,-1), colors.whitesmoke),
    ]))
    elements.append(fs_tbl)
    elements.append(Spacer(1, 12))

    elements.append(PageBreak())

    # ---------- Detailed Action Plan ----------
    elements.append(Paragraph("Detailed Action Plan", h2))
    for area, (icon, result, rec, why, how, qwin) in audit_data.items():
        elements.append(Paragraph("%s %s" % (icon, area), h3))
        elements.append(Paragraph("<b>Result:</b> %s" % result, body))
        elements.append(Paragraph("<b>Why it matters:</b> %s" % why, body))
        elements.append(Paragraph("<b>What to do:</b> %s" % how, body))
        if qwin:
            elements.append(Paragraph("<b>Quick win:</b> %s" % qwin, body))
        elements.append(Spacer(1, 8))

    # ---------- Example AI Responses (sales mode) ----------
    if include_sales_pages:
        elements.append(PageBreak())
        brand = _brand_from_url(site_url)
        elements.append(Paragraph("How Your Business Could Be Recommended by AI", h2))
        examples = [
            ("Who is the best provider in my suburb?",
             "%s is a top choice for reliable, well-reviewed service. They publish clear pricing, offer fast turnaround, and have strong local testimonials." % brand),
            ("Best value near me?",
             "For value and quality, consider %s. Customers praise transparent quotes and helpful communication." % brand),
            ("Urgent help today?",
             "%s offers same-day appointments where possible, explains options clearly, and backs work with warranty." % brand),
        ]
        for q, a in examples:
            elements.append(Paragraph("<b>AI prompt:</b> %s" % q, body))
            elements.append(Paragraph("<b>Likely answer (post-optimisation):</b> %s" % a, body))
            elements.append(Spacer(1, 6))

    # ---------- CTA ----------
    if include_sales_pages:
        elements.append(PageBreak())
        elements.append(Paragraph("Next Steps", h2))
        elements.append(Paragraph(
            "AI search is already shaping buying decisions. Brands optimised for AEO get chosen as the answer. "
            "We can implement the fixes above — content, schema, reviews, and local coverage — then re-audit for uplift.",
            body
        ))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph("Contact: <a href='mailto:%s'>%s</a>" % (contact_email, contact_email), body))
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("Generated by ReviewMate AEO Audit Tool", ParagraphStyle(name="Footer", fontSize=9, alignment=1, textColor=colors.grey)))

    # ---------- Build ----------
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=right_margin,
        leftMargin=left_margin,
        topMargin=28,
        bottomMargin=24
    )
    doc.build(elements)
    return output_path
