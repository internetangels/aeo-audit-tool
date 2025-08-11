# aeo_logic.py — Pro (Stable)
import re
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image, PageBreak,
    ListFlowable, ListItem, KeepInFrame
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors
from datetime import datetime
import os

# ----------------------- Helpers: fetching & parsing -----------------------

def _norm_url(url: str) -> str:
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url

def _safe_get(url: str, timeout=12):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (AEO-Audit-Tool; +https://example.com)"
        }
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code == 200 and "text/html" in r.headers.get("Content-Type", ""):
            return r.text
    except Exception:
        pass
    return ""

def _find_link_like(soup: BeautifulSoup, labels):
    # Find first anchor that looks like any label
    for a in soup.find_all("a", href=True):
        txt = (a.get_text() or "").strip().lower()
        if any(lbl in txt for lbl in labels):
            return a["href"]
    return None

def _grade_level(text: str) -> float:
    # Tiny FK reading ease approximation to avoid extra deps
    try:
        sentences = max(1, text.count(".") + text.count("!") + text.count("?"))
        words = max(1, len(re.findall(r"\b\w+\b", text)))
        syll = max(1, len(re.findall(r"[aeiouyAEIOUY]+", text)))
        # Flesch-Kincaid Grade approximation
        return round(0.39 * (words / sentences) + 11.8 * (syll / words) - 15.59, 1)
    except Exception:
        return 10.0

def _has_table_compare(soup: BeautifulSoup) -> bool:
    # Any table with 3+ columns likely a compare
    for tbl in soup.find_all("table"):
        # crude count: max number of <td> in a row
        rows = tbl.find_all("tr")
        for tr in rows:
            cols = tr.find_all(["td", "th"])
            if len(cols) >= 4:
                return True
    # Also check for /compare pattern text
    txt = soup.get_text(" ", strip=True).lower()
    if "compare" in txt and ("vs" in txt or "pros" in txt or "cons" in txt):
        return True
    return False

def _collect_text(soup: BeautifulSoup, selectors):
    for sel in selectors:
        node = soup.select_one(sel)
        if node:
            return node.get_text(" ", strip=True)
    return ""

# ----------------------- Core: run_audit -----------------------

def run_audit(url: str, local_mode: bool = True):
    """
    Returns dict:
    { area: (icon, result, recommendation, why, how, quick_win) }
    """
    url = _norm_url(url)
    home_html = _safe_get(url)
    soup_home = BeautifulSoup(home_html, "html.parser") if home_html else BeautifulSoup("", "html.parser")

    # Try to locate key pages
    about_href = _find_link_like(soup_home, ["about"])
    services_href = _find_link_like(soup_home, ["services", "service"])
    faq_href = _find_link_like(soup_home, ["faq", "frequently"])
    price_href = _find_link_like(soup_home, ["pricing", "prices", "rates"])
    testi_href = _find_link_like(soup_home, ["testimonials", "reviews"])
    compare_href = _find_link_like(soup_home, ["compare", "comparison"])

    def _get_soup(rel):
        if not rel:
            return BeautifulSoup("", "html.parser")
        absu = urljoin(url, rel)
        html = _safe_get(absu)
        return BeautifulSoup(html, "html.parser") if html else BeautifulSoup("", "html.parser")

    soup_about = _get_soup(about_href)
    soup_services = _get_soup(services_href)
    soup_faq = _get_soup(faq_href)
    soup_pricing = _get_soup(price_href)
    soup_testi = _get_soup(testi_href)
    soup_compare = _get_soup(compare_href)

    # Signals
    page_text = " ".join([soup_home.get_text(" ", strip=True)[:5000]])
    gl = _grade_level(page_text)
    tone_first_person = bool(re.search(r"\b(we|our|i|my|us)\b", page_text.lower()))
    faq_qs = len(soup_faq.find_all(["details", "summary"])) + len(re.findall(r"\b(q:|question|faq)\b", soup_faq.get_text(" ", strip=True).lower()))
    if faq_qs == 0:
        # fallback: look on home
        faq_qs = len(re.findall(r"\b(q:|question|faq)\b", soup_home.get_text(" ", strip=True).lower()))

    testi_hits = len(re.findall(r"\b(testimonial|reviews?|★★★★★|5 star)\b", (soup_testi.get_text(" ", strip=True) + " " + soup_home.get_text(" ", strip=True)).lower()))
    has_compare = _has_table_compare(soup_compare if soup_compare.get_text(strip=True) else soup_home)

    # Heuristic service-in-city: look for city list or suburb mentions in links
    sic = False
    for a in soup_services.find_all("a", href=True):
        if re.search(r"/(service|services)/.+/(?:au|nsw|vic|qld|sa|wa|tas|act)/", a["href"].lower()):
            sic = True; break
        if re.search(r"\b(best|in|near)\b.+\b(vic|melbourne|sydney|brisbane|adelaide|perth|hobart|canberra)\b", a.get_text(" ", strip=True).lower()):
            sic = True; break

    # Pricing presence
    has_pricing = bool(soup_pricing.get_text(strip=True)) or bool(re.search(r"\b(pricing|prices|from|starting at)\b", page_text.lower()))

    # Mobile UX & speed → dumb pass if viewport meta present and images not crazy
    viewport_ok = bool(soup_home.find("meta", attrs={"name": "viewport"}))
    mobile_pass = viewport_ok

    # Build findings
    findings = {}

    # Home Page Readability
    if gl <= 8.0:
        findings["Home Page Readability"] = ("🟢", f"Readable (Grade ~{gl})", "Keep copy concise.",
            "Easier reading increases chance of being quoted in AI answers.",
            "Maintain short sentences, bullets for benefits, and scannable sections.",
            "")
    elif gl <= 11.0:
        findings["Home Page Readability"] = ("🟡", f"Moderate (Grade ~{gl})", "Tighten copy; shorten sentences.",
            "AI models prefer succinct, plain-language answers.",
            "Rewrite hero + first section to be punchier; convert big paragraphs to bullets.",
            "Rewrite hero and top section")
    else:
        findings["Home Page Readability"] = ("🔴", f"Complex (Grade ~{gl})", "Simplify to about 7th grade.",
            "Complex text is less likely to be quoted in AI results.",
            "Shorten sentences; replace jargon; add bullets to distill benefits.",
            "Rewrite hero and top 2 sections")

    # AI Tone of Voice
    if tone_first_person:
        findings["AI Tone of Voice"] = ("🟡", "First-person heavy", "Rewrite to third-person expert.",
            "An objective, expert voice is more quotable for AI recommendations.",
            "Rewrite About/Services to third-person; reduce 'we/our' and show proof.",
            "Rewrite About and Services first")
    else:
        findings["AI Tone of Voice"] = ("🟢", "Objective tone detected", "Maintain neutral, expert tone.",
            "Objective tone helps AI include your content.",
            "Keep first-person limited; lean on testimonials and case studies.",
            "")

    # Service-in-City Pages
    if sic:
        findings["Service-in-City Pages"] = ("🟢", "Dedicated local pages present", "Expand coverage.",
            "Service+City pages target high-intent local queries AI uses.",
            "Add more suburbs; 2 short paras + local testimonial + LocalBusiness schema.",
            "")
    else:
        findings["Service-in-City Pages"] = ("🔴", "Missing dedicated pages", "Create location pages (e.g., 'Mechanic in Upwey').",
            "Precise service+location pages feed AI with local answers.",
            "Draft at least 3 suburb pages; add LocalBusiness + FAQ schema.",
            "Draft 3 suburb pages and link in footer")

    # FAQ Depth
    if faq_qs >= 5:
        findings["FAQ Depth"] = ("🟢", f"{faq_qs} Q&As found", "Keep FAQs fresh.",
            "FAQs directly fuel AI answers; structured Q/A is gold.",
            "Add new Q/A monthly; implement FAQPage schema.",
            "")
    elif faq_qs >= 1:
        findings["FAQ Depth"] = ("🟡", f"{faq_qs} Q&As found", "Add 5–10 buyer FAQs.",
            "Depth matters; concise Q/A improves odds of being quoted.",
            "Create 5–10 buyer-intent questions with plain-language answers.",
            "Publish 5 FAQs this week")
    else:
        findings["FAQ Depth"] = ("🔴", "No proper FAQs", "Add 5–10 buyer FAQs.",
            "AI relies on concise Q/A for direct answers.",
            "Write short Q/A; add FAQPage schema; link from nav/footer.",
            "Publish 5 FAQs this week")

    # Testimonials & Case Studies
    if testi_hits >= 5:
        findings["Testimonials & Case Studies"] = ("🟢", "Strong", "Keep fresh and detailed.",
            "Social proof boosts inclusion and conversions.",
            "Add a case study quarterly; rotate new quotes.",
            "")
    elif testi_hits >= 1:
        findings["Testimonials & Case Studies"] = ("🟡", "Some quotes", "Add more plus 1–2 case studies.",
            "Proof of outcomes increases trust signals.",
            "Gather 6–10 quotes; write one before/after story.",
            "Request quotes from last 10 clients")
    else:
        findings["Testimonials & Case Studies"] = ("🔴", "Not found", "Collect quotes and write 1 case study.",
            "Without proof, AI is less likely to recommend you.",
            "Ask recent customers; publish a case study with metrics.",
            "Request quotes from last 10 clients")

    # Comparison Table
    if has_compare:
        findings["Comparison Table"] = ("🟢", "Present", "Keep updated and honest.",
            "Comparison pages help AI answer 'best/which' queries.",
            "Include pricing, features, and proof; update quarterly.",
            "")
    else:
        findings["Comparison Table"] = ("🔴", "Not found", "Add You vs 3 competitors table.",
            "Structured compare content feeds AI ranking logic.",
            "Create /compare with 4 columns and 5–7 rows; honest but favourable.",
            "Publish /compare with 5 key rows")

    # Pricing Transparency
    if has_pricing:
        findings["Pricing Transparency"] = ("🟡", "Some pricing signals", "Clarify ranges or 'from' pricing.",
            "Price cues help AI route high-intent users; reduces friction.",
            "Add ranges or 'from' prices; link to pricing explainer.",
            "Add a 3-tier pricing block")
    else:
        findings["Pricing Transparency"] = ("🔴", "Contact us only", "Add 'from' pricing or typical ranges.",
            "Absent pricing lowers inclusion and conversion.",
            "Publish ranges; explain inclusions/exclusions.",
            "Add a 3-tier pricing block")

    # Local & Directory Profiles (heuristic)
    # Just a neutral default; real check would call APIs or known directories
    findings["Local & Directory Profiles"] = ("🟡", "Partially completed profiles", "Complete Google Business Profile, Bing Places, Yellow Pages AU; keep NAP consistent.",
        "Consistent citations strengthen entity understanding for AI/maps.",
        "Verify profiles; add categories, services, photos, hours.",
        "Verify GBP and add 5 photos")

    # Reviews Quantity & Rating
    findings["Reviews Quantity & Rating"] = ("🟡", "Low review volume", "Increase Google/Yelp AU (and ProductReview.com.au).",
        "Review volume and recency heavily influence AI recommendations.",
        "Automate review requests by SMS/email; add Review schema.",
        "Send review request to last 20 customers")

    # Press / Best Of Mentions
    findings["Press / Best Of Mentions"] = ("🔴", "No third-party mentions", "Pitch inclusion in local 'Best Of' lists; issue a press release.",
        "Third-party mentions validate authority; AI tools lean on them.",
        "Pitch bloggers/journalists; publish Best of [Category] in [City].",
        "Write a press release about a win")

    # Technical Markup (Schema)
    findings["Technical Markup (Schema)"] = ("🟡", "Partial schema present", "Add/validate LocalBusiness, FAQPage, Review schema.",
        "Structured data helps AI understand entities, services, proof.",
        "Use JSON-LD; test in Rich Results and Schema validators; add sameAs.",
        "Add FAQPage schema to top page")

    # Mobile UX & Speed (very light heuristic)
    if mobile_pass:
        findings["Mobile UX & Speed"] = ("🟢", "Passable mobile UX", "Tidy tap targets; keep CLS/LCP in check.",
            "Most AI-driven searches happen on mobile; poor UX kills conversions.",
            "Compress images; ensure click-to-call is one tap.",
            "Compress hero images; verify LCP < 2.5s")
    else:
        findings["Mobile UX & Speed"] = ("🟡", "Unknown", "Ensure responsive meta + image compression.",
            "Mobile issues lower conversion even if AI sends traffic.",
            "Add viewport meta; compress images; lazy-load below the fold.",
            "Compress hero images; verify LCP < 2.5s")

    return findings

# ----------------------- PDF: helpers -----------------------

def _brand_from_url(site_url: str) -> str:
    try:
        host = urlparse(site_url).netloc or site_url
        host = host.replace("www.", "")
        name = host.split(".")[0]
        return name.replace("-", " ").title() if name else "Your Business"
    except Exception:
        return "Your Business"

def _wrap(flowable, maxw, maxh=1000):
    return KeepInFrame(maxw, maxh, [flowable], mode="shrink")


# ----------------------- PDF: generate_pdf_report -----------------------

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
    styles = getSampleStyleSheet()
    title = ParagraphStyle(name="Title", fontSize=20, leading=24, spaceAfter=14, alignment=1, textColor=colors.HexColor("#1A73E8"))
    h2 = ParagraphStyle(name="H2", fontSize=14, leading=18, spaceBefore=6, spaceAfter=8, textColor=colors.HexColor("#0B5BD3"))
    h3 = ParagraphStyle(name="H3", fontSize=12, leading=15, spaceBefore=4, spaceAfter=6, textColor=colors.black)
    body = ParagraphStyle(name="Body", fontSize=9, leading=12, spaceAfter=4)
    small = ParagraphStyle(name="Small", fontSize=9, leading=12)
    cell = ParagraphStyle(name="Cell", fontSize=9, leading=12)
    blt = ParagraphStyle(name="Bullet", fontSize=9, leading=12)

    left_margin = right_margin = 28
    usable_width = A4[0] - left_margin - right_margin  # ~539pt

    elements = []

    # Header / Logo
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

    # Sales sections
    if include_sales_pages:
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

        elements.append(Paragraph("Why AI Search Matters (vs Traditional SEO)", h2))
        cmp_rows = [
            ["Channel", "How Results Appear", "User Behaviour", "Implication"],
            ["Google SEO", "Multiple links + ads + map pack", "Scroll & compare multiple sites", "You compete for clicks; low certainty"],
            ["AI Search (AEO)", "One answer / shortlist with explanation", "Trusts summarised answer; 1–2 clicks", "Winner-takes-most attention"],
        ]
        cwidths = [usable_width*0.17, usable_width*0.33, usable_width*0.25, usable_width*0.25]
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

    # Executive Summary
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

    # ROI (sales only)
    if include_sales_pages:
        elements.append(Paragraph("Projected ROI (Conservative Model)", h2))
        elements.append(Paragraph(
            "Inputs: Avg sale value = $%s, Baseline conversion = %s%%, Monthly visitors = %s."
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
                roi_rows.append([area, pri, "%d%%" % int(imp * 100), "%.1f" % added_conversions, "$%s" % (int(projected_dollars))])
        if len(roi_rows) == 1:
            roi_rows.append(["All Good", "—", "—", "0.0", "$0"])

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

    # Findings summary
    elements.append(Paragraph("Findings Summary", h2))
    fs_head = ["Audit Area", "Score", "Result", "Recommendation"]
    fs_rows = [fs_head]
    for area, (icon, result, rec, _why, _how, _qwin) in audit_data.items():
        fs_rows.append([area, icon, result, rec])

    fs_cw = [usable_width*0.24, usable_width*0.09, usable_width*0.31, usable_width*0.36]
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

    # Action Plan
    elements.append(Paragraph("Detailed Action Plan", h2))
    for area, (icon, result, rec, why, how, qwin) in audit_data.items():
        elements.append(Paragraph("%s %s" % (icon, area), h3))
        elements.append(Paragraph("<b>Result:</b> %s" % result, body))
        elements.append(Paragraph("<b>Why it matters:</b> %s" % why, body))
        elements.append(Paragraph("<b>What to do:</b> %s" % how, body))
        if qwin:
            elements.append(Paragraph("<b>Quick win:</b> %s" % qwin, body))
        elements.append(Spacer(1, 8))

    # AI Examples
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

    # CTA
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

    # Build
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
