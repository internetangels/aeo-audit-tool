
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image, PageBreak, ListFlowable, ListItem
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from io import BytesIO
from datetime import datetime
import os

# -------------------------------
# Helper scoring
# -------------------------------
_SCORE_MAP = {"🟢": 2, "🟡": 1, "🔴": 0}

def _overall_score(audit_data: dict) -> int:
    if not audit_data:
        return 0
    total = sum(_SCORE_MAP.get(tup[0], 0) for tup in audit_data.values())
    max_total = 2 * len(audit_data)
    return int(round((total / max_total) * 100))

def _collect_bullets(audit_data: dict):
    strengths, weaknesses = [], []
    quick_wins = []
    for area, tup in audit_data.items():
        icon, result, rec, why, how, qwin = tup
        if icon == "🟢":
            strengths.append(f"{area}: {result}")
        elif icon == "🔴":
            weaknesses.append(f"{area}: {result} – {rec}")
            if qwin:
                quick_wins.append(qwin)
        else: # 🟡
            weaknesses.append(f"{area}: {result} – {rec}")
            if qwin:
                quick_wins.append(qwin)
    # de-dup quick wins, keep order
    seen = set()
    qwins_unique = []
    for q in quick_wins:
        if q not in seen:
            qwins_unique.append(q)
            seen.add(q)
    return strengths[:6], weaknesses[:6], qwins_unique[:6]

# -------------------------------
# AEO Audit Engine (v3 - Dual Mode)
# -------------------------------
def run_audit(url: str, local_mode: bool = True) -> dict:
    """
    Returns a dict of audit sections -> (icon, result, recommendation, why_it_matters, how_to_fix, quick_win)
    Icons: 🟢 = good, 🟡 = needs work, 🔴 = missing/poor
    NOTE: This is a heuristic placeholder. Plug in real detection when ready.
    """
    if local_mode:
        geo_example = "Mechanic in Upwey"
        dir_examples = "Google Business Profile, Bing Places, Yellow Pages AU"
        review_focus = "Google & Yelp AU (and ProductReview.com.au)"
        press_note = "local ‘Best Of’ lists, community news, and suburb blogs"
    else:
        geo_example = "Best [Service] in [City]"
        dir_examples = "Google Business Profile, Bing Places, industry directories"
        review_focus = "Google, Yelp, niche review sites"
        press_note = "regional ‘Best Of’ lists and industry roundups"

    data = {
        "Home Page Readability": (
            "🟡",
            "Average clarity",
            "Tighten copy and reduce sentence length",
            "AI answers prefer concise, plain‑language summaries they can quote quickly.",
            "Target a ~7th‑grade reading level, shorten sentences, and surface 3–5 bullet benefits above the fold.",
            "Rewrite hero section in 5 bullet points and 2 short sentences."
        ),
        "AI Tone of Voice": (
            "🟡",
            "Mixed (first‑person + promo)",
            "Rewrite in third‑person expert voice",
            "Neutral, expert tone increases trust and likelihood of being cited by AI systems.",
            "Rewrite key pages as if an independent expert is recommending you; avoid hype.",
            "Rewrite About + Services first to third‑person expert tone."
        ),
        "Service‑in‑City Pages": (
            "🔴",
            "Missing dedicated pages",
            f"Create location pages (e.g., ‘{geo_example}’)",
            "Dedicated service+city pages feed AI with precise local answers and intent signals.",
            "For each suburb/city: 2 short paragraphs, 1 local testimonial, contact CTA, and LocalBusiness + FAQ schema.",
            "Draft 3 priority suburb pages and add to nav/footer sitemap."
        ),
        "FAQ Depth": (
            "🟡",
            "A few basic FAQs",
            "Add 5–10 buyer FAQs with concise answers",
            "Q&A blocks map directly to how users ask AI and power rich answers.",
            "Add specific pricing, turnaround, warranty, and service‑area FAQs with 1–3 sentence answers; add FAQPage schema.",
            "Add 5 FAQs to top 2 service pages this week."
        ),
        "Testimonials & Case Studies": (
            "🔴",
            "Weak social proof",
            "Create testimonials page and 1–2 case studies",
            "Social proof is a strong recommendation signal for AI and a conversion driver for humans.",
            "Collect 6–10 quotes with names/suburbs; add a ‘Results’ story with before/after and photo if possible.",
            "Email last 10 customers for a 2‑line quote and star rating."
        ),
        "Comparison Table": (
            "🔴",
            "No competitor comparison",
            "Add a simple comparison table (You vs 3 competitors)",
            "Side‑by‑side comparisons are frequently quoted in AI overviews for ‘X vs Y’ queries.",
            "4 columns: You vs 3 competitors; rows: features, warranty, response time, price band, reviews.",
            "Draft a 5‑row table and publish under /compare."
        ),
        "Pricing Transparency": (
            "🟡",
            "‘Contact us’ only",
            "Add ‘from’ pricing or ranges",
            "Price signals help AI route high‑intent users and reduce friction.",
            "Publish ‘from’ pricing or typical ranges with inclusions/exclusions; link to a pricing explainer.",
            "Add a ‘Pricing’ section with 3 tiers today."
        ),
        "Local & Directory Profiles": (
            "🟡",
            "Partially completed profiles",
            f"Complete {dir_examples} and keep NAP consistent",
            "Consistent profiles and citations strengthen local entity understanding for AI and maps.",
            "Ensure name‑address‑phone matches everywhere; add categories, services, photos, hours.",
            "Verify/complete Google Business Profile and add 5 photos."
        ),
        "Reviews Quantity & Rating": (
            "🟡",
            "Low review volume",
            f"Increase {review_focus}; ask after completed jobs",
            "Review volume and recency heavily influence AI recommendations.",
            "Automate review requests by SMS/email post‑job; showcase rating on site with Review schema.",
            "Send a review request to last 20 customers."
        ),
        "Press / ‘Best Of’ Mentions": (
            "🔴",
            "No third‑party mentions",
            f"Pitch inclusion in {press_note}",
            "Third‑party mentions validate authority; AI tools lean on them to avoid bias.",
            "Pitch local bloggers/journalists; publish a ‘Best of [Category] in [City]’ round‑up with transparent criteria.",
            "Write a press release about a customer win or new service launch."
        ),
        "Technical Markup (Schema)": (
            "🟡",
            "Partial schema present",
            "Add/validate LocalBusiness, FAQPage, Review schema",
            "Structured data helps AI understand entities, services, and proof.",
            "Use JSON‑LD; test in Rich Results & Schema validators; add sameAs links to major profiles.",
            "Add FAQPage schema to top service page."
        ),
        "Mobile UX & Speed": (
            "🟢",
            "Passable mobile UX",
            "Tidy tap targets; keep CLS/LCP in check",
            "Most AI‑driven searches happen on mobile; poor UX kills conversions.",
            "Ensure click‑to‑call/WhatsApp are 1‑tap; compress images; lazy‑load below the fold.",
            "Compress hero images and verify LCP < 2.5s."
        ),
    }
    return data

# --------------------------------------------
# Premium PDF with Executive Summary + Action Plan
# --------------------------------------------
def generate_pdf_report(audit_data: dict, output_path: str, logo_path: str = None, contact_email: str = "carmine@internetangels.com.au", site_url: str = ""):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=28, leftMargin=28, topMargin=28, bottomMargin=24)
    styles = getSampleStyleSheet()
    title = ParagraphStyle(name="Title", fontSize=20, spaceAfter=14, alignment=1, textColor=colors.HexColor("#1A73E8"))
    h2 = ParagraphStyle(name="H2", fontSize=14, spaceAfter=8, textColor=colors.HexColor("#0B5BD3"))
    h3 = ParagraphStyle(name="H3", fontSize=12, spaceAfter=6, textColor=colors.black)
    small = ParagraphStyle(name="Small", fontSize=9, leading=12)
    cell = ParagraphStyle(name="Cell", fontSize=9, leading=11)
    footer = ParagraphStyle(name="Footer", fontSize=9, alignment=1, textColor=colors.grey)

    elements = []

    # Header / Logo
    if logo_path and os.path.exists(logo_path):
        elements.append(Image(logo_path, width=400, height=60))
        elements.append(Spacer(1, 6))

    # Title Block
    elements.append(Paragraph("AI Search (AEO) Audit & Action Plan", title))
    meta = f"Website: {site_url or 'N/A'}  •  Date: {datetime.today().strftime('%d %b %Y')}"
    elements.append(Paragraph(meta, small))
    elements.append(Spacer(1, 6))

    # Executive Summary
    score = _overall_score(audit_data)
    strengths, weaknesses, quick_wins = _collect_bullets(audit_data)

    elements.append(Paragraph("Executive Summary", h2))
    elements.append(Paragraph(f"Overall AEO Readiness Score: <b>{score}%</b>", small))
    elements.append(Spacer(1, 2))

    # Strengths / Weaknesses / Quick Wins as bullet lists
    bl_style = ParagraphStyle(name="Bullet", fontSize=9, leading=12)
    if strengths:
        elements.append(Paragraph("Strengths", h3))
        elements.append(ListFlowable([ListItem(Paragraph(s, bl_style)) for s in strengths], bulletType='bullet', leftIndent=10))
        elements.append(Spacer(1, 4))

    if weaknesses:
        elements.append(Paragraph("Weaknesses", h3))
        elements.append(ListFlowable([ListItem(Paragraph(w, bl_style)) for w in weaknesses], bulletType='bullet', leftIndent=10))
        elements.append(Spacer(1, 4))

    if quick_wins:
        elements.append(Paragraph("Quick Wins (next 7 days)", h3))
        elements.append(ListFlowable([ListItem(Paragraph(q, bl_style)) for q in quick_wins], bulletType='bullet', leftIndent=10))
        elements.append(Spacer(1, 6))

    # Summary Table
    data_rows = [["Audit Area", "Score", "Result", "Recommendation"]]
    for area, tup in audit_data.items():
        icon, result, rec, *_ = tup
        data_rows.append([Paragraph(area, cell), Paragraph(icon, cell), Paragraph(result, cell), Paragraph(rec, cell)])
    table = Table(data_rows, colWidths=[120, 40, 160, 160])
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
    elements.append(Spacer(1, 8))

    elements.append(PageBreak())

    # Action Plan
    elements.append(Paragraph("Detailed Action Plan", h2))
    for area, tup in audit_data.items():
        icon, result, rec, why, how, qwin = tup
        elements.append(Paragraph(f"{icon} {area}", h3))
        elements.append(Paragraph(f"<b>Result:</b> {result}", small))
        elements.append(Paragraph(f"<b>Why it matters:</b> {why}", small))
        elements.append(Paragraph(f"<b>What to do:</b> {how}", small))
        if qwin:
            elements.append(Paragraph(f"<b>Quick win:</b> {qwin}", small))
        elements.append(Spacer(1, 6))

    elements.append(PageBreak())

    # CTA
    elements.append(Paragraph("Next Steps", h2))
    elements.append(Paragraph(
        "Want a hands-off implementation? Internet Angels can write, design, and ship everything above — from service-in-city pages and FAQs to schema and comparison tables — then re-audit for gains.",
        small
    ))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(f"📧 <b>Contact:</b> <a href='mailto:{contact_email}'>{contact_email}</a>", small))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("Generated by ReviewMate AEO Audit Tool", footer))

    # Build
    doc.build(elements)
    buffer.seek(0)
    with open(output_path, "wb") as f:
        f.write(buffer.read())
    return output_path
