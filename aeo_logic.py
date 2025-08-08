from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image, PageBreak, ListFlowable, ListItem
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from io import BytesIO
from datetime import datetime
from bs4 import BeautifulSoup
import requests
import re
import time
import os

# -------------------------------
# HTTP fetch helpers
# -------------------------------
DEFAULT_HEADERS = {
    "User-Agent": "ReviewMate-AEO/1.0 (+https://reviewmate.example)",
    "Accept-Language": "en-AU,en;q=0.9",
}

def _fetch(url, timeout=10):
    try:
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        if r.status_code == 403:
            alt = dict(DEFAULT_HEADERS)
            alt["User-Agent"] = "Mozilla/5.0 (compatible; ReviewMateAuditBot/1.0)"
            r = requests.get(url, headers=alt, timeout=timeout)
        if r.ok:
            return r.text
    except requests.RequestException:
        return None
    return None

def _pick_candidate_urls(base_url):
    base = base_url.rstrip("/")
    cands = [
        base + "/",
        base + "/about",
        base + "/services",
        base + "/service",
        base + "/faq",
        base + "/faqs",
        base + "/testimonials",
        base + "/reviews",
        base + "/pricing",
        base + "/compare",
        base + "/contact",
    ]
    out = []
    seen = set()
    for u in cands:
        if u not in seen:
            out.append(u)
            seen.add(u)
    return out

def fetch_site(base_url, max_pages=8, sleep_between=0.5):
    pages = {}
    for u in _pick_candidate_urls(base_url)[:max_pages]:
        html = _fetch(u)
        if html:
            pages[u] = html
        time.sleep(sleep_between)
    return pages

# -------------------------------
# Content detectors (fast + simple)
# -------------------------------
def _reading_grade_estimate(text):
    # Lightweight Flesch-Kincaid-ish estimate
    text = re.sub(r"[^a-zA-Z0-9\.!? ]+", " ", text)
    sentences = re.split(r"[\.!?]+", text)
    words = re.findall(r"\w+", text)
    if not words or not sentences:
        return 0.0
    syllables = 0
    vowels = re.compile(r"[aeiouyAEIOUY]+")
    for w in words:
        syllables += len(vowels.findall(w))
    sent_count = len([s for s in sentences if s.strip()])
    if sent_count == 0:
        sent_count = 1
    grade = 0.39 * (len(words) / float(sent_count)) + 11.8 * (syllables / float(len(words))) - 15.59
    return round(grade, 1)

def _third_person_signal(text):
    t = text.lower()
    first = len(re.findall(r"\b(we|our|us|i|my)\b", t))
    third = len(re.findall(r"\b(they|their|the company|the team)\b", t))
    if third > first:
        return "third"
    if first > third:
        return "first"
    return "mixed"

def _has_faq(soup):
    text = soup.get_text(" ").lower()
    q_count = 0
    q_count += len(re.findall(r"\b(q:|question)\b", text))
    q_count += len(soup.select("details summary"))
    q_count += len(soup.select("[itemtype*='FAQPage']"))
    return q_count >= 2

def _testimonial_score(soup):
    text = soup.get_text(" ").lower()
    hits = 0
    hits += len(re.findall(r"testimonial|what our customers|5 star|★★★★★", text))
    hits += len(re.findall(r"\"[^\"]+\"", text))
    return hits

def _has_comparison_table(soup):
    if soup.find("table"):
        txt = soup.get_text(" ").lower()
        return (" vs " in txt) or ("compare" in txt) or ("comparison" in txt)
    return False

# -------------------------------
# Scoring helpers
# -------------------------------
_SCORE_MAP = {"🟢": 2, "🟡": 1, "🔴": 0}

def _score_summary(audit_data):
    total = sum(_SC ORE_MAP.get(t[0], 0) for t in audit_data.values())
    max_total = 2 * len(audit_data) if audit_data else 1
    return int(round((total / float(max_total)) * 100))

def _collect_lists(audit_data):
    strengths, weaknesses, qw = [], [], []
    for k, (icon, result, rec, why, how, qwin) in audit_data.items():
        if icon == "🟢":
            strengths.append("%s: %s" % (k, result))
        else:
            weaknesses.append("%s: %s — %s" % (k, result, rec))
            if qwin:
                qw.append(qwin)
    seen = set()
    out_qw = []
    for q in qw:
        if q not in seen:
            out_qw.append(q)
            seen.add(q)
    return strengths[:6], weaknesses[:6], out_qw[:6]

# -------------------------------
# Audit engine (data-driven)
# -------------------------------
def run_audit(url, local_mode=True):
    if local_mode:
        geo_example = "Mechanic in Upwey"
        dir_examples = "Google Business Profile, Bing Places, Yellow Pages AU"
        review_focus = "Google and Yelp AU (and ProductReview.com.au)"
        press_note = "local Best Of lists, community news, and suburb blogs"
    else:
        geo_example = "Best [Service] in [City]"
        dir_examples = "Google Business Profile, Bing Places, industry directories"
        review_focus = "Google, Yelp, niche review sites"
        press_note = "regional Best Of lists and industry roundups"

    data = {
        "Home Page Readability": ("🟡", "Average clarity", "Tighten copy; shorter sentences",
            "AI answers prefer concise, plain-language summaries they can quote quickly.",
            "Target ~7th-grade reading, add bullets above the fold.", "Rewrite hero in bullets"),
        "AI Tone of Voice": ("🟡", "Mixed (first-person + promo)", "Rewrite in third-person expert voice",
            "Neutral expert tone increases trust and likelihood of citation by AI systems.",
            "Rewrite key pages as if an independent expert is recommending you; avoid hype.", "Rewrite About and Services"),
        "Service-in-City Pages": ("🔴", "Missing dedicated pages", "Create location pages (e.g., %s)" % geo_example,
            "Dedicated service+city pages feed AI with precise local answers and intent signals.",
            "For each suburb/city: 2 short paragraphs, 1 local testimonial, contact CTA, and LocalBusiness + FAQ schema.",
            "Draft 3 suburb pages and link in footer"),
        "FAQ Depth": ("🟡", "A few basic FAQs", "Add 5-10 buyer FAQs with concise answers",
            "Q&A blocks map directly to how users ask AI and power rich answers.",
            "Add pricing/turnaround/warranty/service-area FAQs; add FAQPage schema.", "Add 5 FAQs to a top service page"),
        "Testimonials & Case Studies": ("🔴", "Weak social proof", "Create testimonials page and 1-2 case studies",
            "Social proof is a strong recommendation signal for AI and a conversion driver for humans.",
            "Collect 6-10 quotes with names/suburbs; add a Results story with before/after.", "Email last 10 customers for quotes"),
        "Comparison Table": ("🔴", "No competitor comparison", "Add a simple comparison table (You vs 3 competitors)",
            "Side-by-side comparisons are frequently quoted in AI X vs Y.",
            "4 columns: You vs 3 competitors; rows: features, warranty, response time, price band, reviews.",
            "Publish /compare with 5 key rows"),
        "Pricing Transparency": ("🟡", "Contact us only", "Add from pricing or ranges",
            "Price signals help AI route high-intent users and reduce friction.",
            "Publish from pricing or typical ranges; link to a pricing explainer.", "Add a 3-tier pricing block"),
        "Local & Directory Profiles": ("🟡", "Partially completed profiles", "Complete %s and keep NAP consistent" % dir_examples,
            "Consistent profiles and citations strengthen local entity understanding for AI and maps.",
            "Ensure name-address-phone matches everywhere; add categories, services, photos, hours.",
            "Verify Google Business Profile and add 5 photos"),
        "Reviews Quantity & Rating": ("🟡", "Low review volume", "Increase %s; ask after completed jobs" % review_focus,
            "Review volume and recency heavily influence AI recommendations.",
            "Automate review requests by SMS/email post-job; add Review schema.", "Send review request to last 20 customers"),
        "Press / Best Of Mentions": ("🔴", "No third-party mentions", "Pitch inclusion in %s" % press_note,
            "Third-party mentions validate authority; AI tools lean on them to avoid bias.",
            "Pitch bloggers/journalists; publish Best of [Category] in [City] with clear criteria.", "Write a press release about a win"),
        "Technical Markup (Schema)": ("🟡", "Partial schema present", "Add/validate LocalBusiness, FAQPage, Review schema",
            "Structured data helps AI understand entities, services, and proof.",
            "Use JSON-LD; test in Rich Results and Schema validators; add sameAs links.", "Add FAQPage schema to top page"),
        "Mobile UX & Speed": ("🟢", "Passable mobile UX", "Tidy tap targets; keep CLS/LCP in check",
            "Most AI-driven searches happen on mobile; poor UX kills conversions.",
            "Ensure click-to-call is 1 tap; compress images; lazy-load below the fold.", "Compress hero images, verify LCP < 2.5s"),
    }

    # Try to fetch live pages and override with signals
    try:
        fetched = fetch_site(url)
        soups = [BeautifulSoup(h, "html.parser") for h in fetched.values()] if fetched else []
        page_texts = [s.get_text(" ") for s in soups]

        # Readability: use longest page
        if page_texts:
            longest_idx = max(range(len(page_texts)), key=lambda i: len(page_texts[i]))
            grade = _reading_grade_estimate(page_texts[longest_idx])
        else:
            grade = 10.0

        if grade <= 8:
            data["Home Page Readability"] = ("🟢", "Clear (Grade ~%s)" % grade, "Keep concise structure",
                "AI prefers succinct, scannable copy.", "Maintain short sentences, bullets, descriptive headings.",
                "Keep hero to 2 lines plus 3 bullets")
        elif grade <= 10:
            data["Home Page Readability"] = ("🟡", "Moderate (Grade ~%s)" % grade, "Tighten copy; shorten sentences",
                "Easier reading improves chance of being quoted.", "Trim long sentences; add bullets to key benefits.",
                "Rewrite hero and first section")
        else:
            data["Home Page Readability"] = ("🔴", "Complex (Grade ~%s)" % grade, "Simplify to about 7th grade",
                "Complex text is less likely to be quoted by AI.", "Shorten sentences; swap jargon for plain language.",
                "Rewrite hero and top 2 sections")

        # Tone
        if page_texts:
            tones = [_third_person_signal(t) for t in page_texts]
            if tones.count("third") > len(tones) / 2.0:
                data["AI Tone of Voice"] = ("🟢", "Third-person", "Maintain expert voice",
                    "Neutral, expert tone increases trust and citations.", "Keep independent expert voice; avoid hype.",
                    "Review About and Services for consistency")
            elif tones.count("first") > len(tones) / 2.0:
                data["AI Tone of Voice"] = ("🔴", "First-person heavy", "Rewrite to third-person expert",
                    "Objective tone is preferred in AI answers.", "Rewrite key pages to expert third-person; reduce we/our.",
                    "Rewrite About and Services first")
            else:
                data["AI Tone of Voice"] = ("🟡", "Mixed", "Normalize to expert third-person",
                    "Consistency improves trust and extractability.", "Edit pages to one consistent expert voice.",
                    "Start with homepage")

        # FAQ
        any_faq = any(_has_faq(s) for s in soups) if soups else False
        if any_faq:
            data["FAQ Depth"] = ("🟢", "Found usable FAQs", "Expand over time",
                "Q&A mirrors how users ask AI questions.", "Add pricing/turnaround/warranty FAQs; add FAQPage schema.",
                "Add 3 FAQs to top service page")
        else:
            data["FAQ Depth"] = ("🔴", "No proper FAQs", "Add 5-10 buyer FAQs",
                "Directly fuels answer engines and rich results.", "Write concise Q&As; implement FAQPage schema.",
                "Publish 5 FAQs this week")

        # Testimonials
        tcount = 0
        if soups:
            for s in soups:
                tcount += _testimonial_score(s)
        if tcount >= 8:
            data["Testimonials & Case Studies"] = ("🟢", "Strong", "Keep fresh and detailed",
                "Social proof boosts AI recommendations and conversions.", "Rotate new quotes and add case studies.",
                "Collect 2 fresh quotes monthly")
        elif tcount >= 3:
            data["Testimonials & Case Studies"] = ("🟡", "Some quotes", "Add more plus 1-2 case studies",
                "Proof of outcomes increases trust signals.", "Gather 6-10 quotes; add one before/after story.",
                "Request quotes from last 10 clients")
        else:
            data["Testimonials & Case Studies"] = ("🔴", "Missing/weak", "Create testimonials page plus case study",
                "AI and users rely on proof points.", "Collect 6-10 quotes; publish one detailed case study.",
                "Email last 10 customers for a 2-line quote")

        # Comparison table
        any_compare = False
        if soups:
            any_compare = any(_has_comparison_table(s) for s in soups)
        if any_compare:
            data["Comparison Table"] = ("🟢", "Present", "Ensure clarity and fairness",
                "Side-by-side tables are cited in AI X vs Y.", "Keep factual; add features, warranty, price range.",
                "Add a row for response time")
        else:
            data["Comparison Table"] = ("🔴", "Not found", "Add You vs 3 competitors table",
                "Helps AI for Which is best queries.", "Create a 4-column table with honest comparisons.",
                "Publish /compare with 5 key rows")

    except Exception:
        # If fetch fails, keep baseline
        pass

    return data

# -------------------------------
# PDF (Executive Summary + Action Plan)
# -------------------------------
def _collect_lists_for_pdf(audit_data):
    strengths, weaknesses, qw = [], [], []
    for k, (icon, result, rec, why, how, qwin) in audit_data.items():
        if icon == "🟢":
            strengths.append("%s: %s" % (k, result))
        else:
            weaknesses.append("%s: %s — %s" % (k, result, rec))
            if qwin:
                qw.append(qwin)
    seen = set()
    out_qw = []
    for q in qw:
        if q not in seen:
            out_qw.append(q)
            seen.add(q)
    return strengths[:6], weaknesses[:6], out_qw[:6]

def generate_pdf_report(audit_data, output_path, logo_path=None, contact_email="carmine@internetangels.com.au", site_url=""):
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
    elements.append(Paragraph("AI Search (AEO) Audit and Action Plan", title))
    meta = "Website: %s  •  Date: %s" % (site_url or "N/A", datetime.today().strftime("%d %b %Y"))
    elements.append(Paragraph(meta, small))
    elements.append(Spacer(1, 6))

    # Executive Summary
    strengths, weaknesses, quick_wins = _collect_lists_for_pdf(audit_data)
    elements.append(Paragraph("Executive Summary", h2))
    # simple score based on icons
    total = sum(_SCORE_MAP.get(t[0], 0) for t in audit_data.values())
    max_total = 2 * len(audit_data) if audit_data else 1
    score_pct = int(round((total / float(max_total)) * 100))
    elements.append(Paragraph("Overall AEO Readiness Score: <b>%d%%</b>" % score_pct, small))
    elements.append(Spacer(1, 2))

    bl_style = ParagraphStyle(name="Bullet", fontSize=9, leading=12)
    if strengths:
        elements.append(Paragraph("Strengths", h3))
        elements.append(ListFlowable([ListItem(Paragraph(s, bl_style)) for s in strengths], bulletType="bullet", leftIndent=10))
        elements.append(Spacer(1, 4))
    if weaknesses:
        elements.append(Paragraph("Weaknesses", h3))
        elements.append(ListFlowable([ListItem(Paragraph(w, bl_style)) for w in weaknesses], bulletType="bullet", leftIndent=10))
        elements.append(Spacer(1, 4))
    if quick_wins:
        elements.append(Paragraph("Quick Wins (next 7 days)", h3))
        elements.append(ListFlowable([ListItem(Paragraph(q, bl_style)) for q in quick_wins], bulletType="bullet", leftIndent=10))
        elements.append(Spacer(1, 6))

    # Summary Table
    data_rows = [["Audit Area", "Score", "Result", "Recommendation"]]
    for area, tup in audit_data.items():
        icon, result, rec, _why, _how, _qwin = tup
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
        elements.append(Paragraph("%s %s" % (icon, area), h3))
        elements.append(Paragraph("<b>Result:</b> %s" % result, small))
        elements.append(Paragraph("<b>Why it matters:</b> %s" % why, small))
        elements.append(Paragraph("<b>What to do:</b> %s" % how, small))
        if qwin:
            elements.append(Paragraph("<b>Quick win:</b> %s" % qwin, small))
        elements.append(Spacer(1, 6))

    elements.append(PageBreak())

    # CTA
    elements.append(Paragraph("Next Steps", h2))
    elements.append(Paragraph(
        "Want a hands-off implementation? Internet Angels can write, design, and ship everything above "
        "— from service-in-city pages and FAQs to schema and comparison tables — then re-audit for gains.",
        small
    ))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph("Contact: %s" % ("<a href='mailto:%s'>%s</a>" % (contact_email, contact_email)), small))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("Generated by ReviewMate AEO Audit Tool", footer))

    doc.build(elements)
    buffer.seek(0)
    with open(output_path, "wb") as f:
        f.write(buffer.read())
    return output_path
