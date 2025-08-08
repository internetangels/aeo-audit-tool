
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image, PageBreak
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from io import BytesIO
import os

# -------------------------------
# AEO Audit Engine (v2 - Detailed)
# -------------------------------

def run_audit(url: str):
    """
    Returns a dict of audit sections -> (icon, result, recommendation, why_it_matters, how_to_fix)
    Icons: 🟢 = good, 🟡 = needs work, 🔴 = missing/poor
    """
    # NOTE: This is a deterministic placeholder.
    # Hook your scraping/analysis here and fill in the tuples dynamically.
    data = {
        "Home Page Readability": (
            "🟡",
            "Average",
            "Simplify language and shorten paragraphs.",
            "AI assistants prefer concise, plain-language summaries they can quote quickly.",
            "Target a 7th-grade reading level; shorten sentences; add bullet points for key benefits."
        ),
        "Service Page Keywords": (
            "🔴",
            "Missing",
            "Add clear service names like 'car repairs', 'mechanic', etc.",
            "Explicit service language helps AI map your page to buyer-intent queries ('best mechanic near me').",
            "Add service names to H1/H2s and first paragraph; include natural phrases like 'car repairs in Upwey'."
        ),
        "Local Relevance": (
            "🟢",
            "Strong",
            "Well-targeted to Upwey area; keep it up.",
            "Location signals are essential for AI to recommend local providers.",
            "Maintain suburb and landmark references; add embedded map and NAP in footer."
        ),
        "Mobile Friendliness": (
            "🟢",
            "Pass",
            "Site is responsive.",
            "Most AI-driven searches happen on mobile; poor UX reduces conversions.",
            "Verify tap targets, font sizes, CLS/LCP basics; ensure phone/email are one-tap actions."
        ),
        "AI Tone of Voice": (
            "🟡",
            "Mixed",
            "Rewrite in third-person expert voice at ~7th grade.",
            "Neutral, expert tone increases trust and likelihood of citation by AI systems.",
            "Rewrite key pages as an 'independent expert' describing why you’re the top choice."
        ),
        "Testimonials & Reviews": (
            "🔴",
            "Weak",
            "Add testimonials and star ratings page.",
            "Social proof is a strong ranking/recommendation signal for AI and humans.",
            "Collect 5–10 detailed quotes with names/suburbs; add review schema if applicable."
        ),
        "Service-in-City Pages": (
            "🔴",
            "Missing",
            "Create pages like 'Mechanic in Upwey', 'Car Repairs Belgrave'.",
            "Dedicated service+city pages feed AI with precise local answers.",
            "For each suburb: write 2 short paras, 1 testimonial, contact CTA, and LocalBusiness/FAQ schema."
        ),
        "FAQs & Case Studies": (
            "🟡",
            "Some",
            "Expand FAQ; add 1–2 case studies.",
            "Q&A blocks map directly to how users ask AI; case studies prove outcomes.",
            "Add 5–10 buyer FAQs with concise answers; publish 1–2 before/after stories."
        ),
        "Comparison Table": (
            "🔴",
            "Not found",
            "Add simple competitor comparison.",
            "Side-by-side comparisons are frequently quoted in AI overviews for 'X vs Y' queries.",
            "Create a 4-column table (You vs 3 competitors): features, warranty, price range, response time."
        ),
    }
    return data

# --------------------------------------------
# Polished PDF with Action Plan (sales forward)
# --------------------------------------------

def generate_pdf_report(audit_data: dict, output_path: str, logo_path: str = None, contact_email: str = "carmine@internetangels.com.au"):
    """
    Builds a branded, client-friendly PDF that includes:
      - Title + logo
      - Traffic-light summary table
      - Action Plan for AI SEO (why it matters + how to fix for each item)
      - CTA
    Returns the written output_path.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=24)
    styles = getSampleStyleSheet()
    title = ParagraphStyle(name="Title", fontSize=20, spaceAfter=18, alignment=1, textColor=colors.HexColor("#1A73E8"))
    h2 = ParagraphStyle(name="H2", fontSize=14, spaceAfter=10, textColor=colors.HexColor("#0B5BD3"))
    h3 = ParagraphStyle(name="H3", fontSize=12, spaceAfter=6, textColor=colors.black)
    small = ParagraphStyle(name="Small", fontSize=9, leading=12)
    cell = ParagraphStyle(name="Cell", fontSize=9, leading=11)
    footer = ParagraphStyle(name="Footer", fontSize=9, alignment=1, textColor=colors.grey)

    elements = []

    # Header / Logo
    if logo_path and os.path.exists(logo_path):
        elements.append(Image(logo_path, width=400, height=60))
        elements.append(Spacer(1, 12))

    elements.append(Paragraph("AI SEO (AEO) Compliance Report", title))
    elements.append(Paragraph("Generated by ReviewMate AEO Audit Tool", small))
    elements.append(Spacer(1, 6))

    # Summary Table
    data = [["Audit Area", "Score", "Result", "Recommendation"]]
    for area, tup in audit_data.items():
        icon, result, rec, *_rest = tup
        data.append([Paragraph(area, cell), Paragraph(icon, cell), Paragraph(result, cell), Paragraph(rec, cell)])

    table = Table(data, colWidths=[120, 40, 160, 160])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A73E8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
    ]))
    elements.append(table)

    elements.append(Spacer(1, 18))
    elements.append(Paragraph("Action Plan for AI Search Readiness", h2))
    elements.append(Paragraph("Exactly what to change to reach optimal AEO performance.", small))
    elements.append(Spacer(1, 6))

    # Action Plan Items
    for area, tup in audit_data.items():
        icon, result, rec, why, how = tup
        elements.append(Paragraph(f"{icon} {area}", h3))
        elements.append(Paragraph(f"<b>Why it matters:</b> {why}", small))
        elements.append(Paragraph(f"<b>What to do:</b> {how}", small))
        elements.append(Spacer(1, 10))

    elements.append(PageBreak())

    # CTA
    elements.append(Paragraph("Next Steps", h2))
    elements.append(Paragraph(
        "Want a hands-off implementation? Internet Angels can write, design, and ship everything above "
        "— from service-in-city pages and FAQs to schema and comparison tables — then re-audit for gains.",
        small
    ))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"📧 <b>Contact:</b> <a href='mailto:{contact_email}'>{contact_email}</a>", small))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph("Generated by ReviewMate AEO Audit Tool", footer))

    # Build
    doc.build(elements)
    buffer.seek(0)
    with open(output_path, "wb") as f:
        f.write(buffer.read())
    return output_path
