
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image, PageBreak, ListFlowable, ListItem
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from io import BytesIO
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests, re, time, os

# ---------------------------------
# HTTP fetch helpers (polite + robust)
# ---------------------------------
DEFAULT_HEADERS = {
    "User-Agent": "ReviewMate-AEO/1.0 (+https://reviewmate.local)",
    "Accept-Language": "en-AU,en;q=0.9",
}

def _fetch(url: str, timeout: int = 10) -> str | None:
    try:
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        if r.status_code == 403:
            alt = DEFAULT_HEADERS.copy()
            alt["User-Agent"] = "Mozilla/5.0 (compatible; ReviewMateAuditBot/1.0)"
            r = requests.get(url, headers=alt, timeout=timeout)
        if r.ok:
            return r.text
    except requests.RequestException:
        return None
    return None

def _pick_candidate_urls(base_url: str) -> list[str]:
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
    seen, out = set(), []
    for u in cands:
        if u not in seen:
            out.append(u); seen.add(u)
    return out

def fetch_site(base_url: str, max_pages: int = 8, sleep_between: float = 0.5) -> dict[str, str]:
    pages: dict[str, str] = {}
    for u in _pick_candidate_urls(base_url)[:max_pages]:
        html = _fetch(u)
        if html:
            pages[u] = html
        time.sleep(sleep_between)
    return pages

# ---------------------------------
# Content detectors (fast + simple)
# ---------------------------------
def _reading_grade_estimate(text: str) -> float:
    # Lightweight Flesch-Kincaid approximation
    text = re.sub(r"[^a-zA-Z0-9\.!? ]+", " ", text)
    sentences = re.split(r"[.!?]+", text)
    words = re.findall(r"\w+", text)
    if not words or not sentences:
        return 0.0
    syllables = sum(len(re.findall(r"[aeiouyAEIOUY]+", w)) for w in words)
    grade = 0.39 * (len(words) / max(1, len([s for s in sentences if s.strip()]))) + 11.8 * (syllables / max(1, len(words))) - 15.59
    return round(grade, 1)

def _third_person_signal(text: str) -> str:
    t = text.lower()
    first = len(re.findall(r"\b(we|our|us|i|my)\b", t))
    third = len(re.findall(r"\b(they|their|the company|the team)\b", t))
    if third > first: return "third"
    if first > third: return "first"
    return "mixed"

def _has_faq(soup: BeautifulSoup) -> bool:
    text = soup.get_text(" ").lower()
    q_count = len(re.findall(r"\b(q:|question)\b", text)) + len(soup.select("details summary")) + len(soup.select("[itemtype*='FAQPage']"))
    return q_count >= 2

def _testimonial_score(soup):
    # Count common testimonial signals + quoted snippets (ASCII-safe)
    text = soup.get_text(" ").lower()
    hits = 0
    hits += len(re.findall(r"\b(testimonial|what our customers|reviews?)\b", text))
    hits += len(re.findall(r"5\s*-?\s*star", text))
    # Optional: count star runs (5 or more solid stars) using the ASCII-safe char directly
    hits += len(re.findall(r"★★★★★", text))
    # Count any reasonably long quoted sentence using straight quotes
    hits += len(re.findall(r"\"[^\"]{10,}\"", text))
    return hits


def _has_comparison_table(soup: BeautifulSoup) -> bool:
    if soup.find("table"):
        txt = soup.get_text(" ").lower()
        return (" vs " in txt) or ("compare" in txt) or ("comparison" in txt)
    return False

def _page_text_len(html: str) -> int:
    return len(BeautifulSoup(html, "html.parser").get_text(" "))

# ---------------------------------
# Scoring helpers
# ---------------------------------
_SCORE_MAP = {"🟢": 2, "🟡": 1, "🔴": 0}

def _overall_score(audit_data: dict) -> int:
    if not audit_data:
        return 0
    total = sum(_SCORE_MAP.get(tup[0], 0) for tup in audit_data.values())
    max_total = 2 * len(audit_data)
    return int(round((total / max_total) * 100))

def _collect_bullets(audit_data: dict):
    strengths, weaknesses, quick_wins = [], [], []
    for area, tup in audit_data.items():
        icon, result, rec, why, how, qwin = tup
        if icon == "🟢":
            strengths.append(f"{area}: {result}")
        elif icon == "🔴":
            weaknesses.append(f"{area}: {result} – {rec}")
            if qwin:
                quick_wins.append(qwin)
        else:  # 🟡
            weaknesses.append(f"{area}: {result} – {rec}")
            if qwin:
                quick_wins.append(qwin)
    # de-dup quick wins
    seen, unique_qwins = set(), []
    for q in quick_wins:
        if q not in seen:
            unique_qwins.append(q); seen.add(q)
    return strengths[:6], weaknesses[:6], unique_qwins[:6]

# ---------------------------------
# Audit engine (v4 - data-driven)
# ---------------------------------
def run_audit(url: str, local_mode: bool = True) -> dict:
    """Return dict: area -> (icon, result, recommendation, why, how, quick_win)"""
    # Local/global copy variations
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

    # Baseline template (will be overridden by signals where available)
    data = {
        "Home Page Readability": ("🟡", "Average clarity", "Tighten copy; shorter sentences",
            "AI answers prefer concise, plain‑language summaries they can quote quickly.",
            "Target ~7th‑grade reading, add bullets above the fold.", "Rewrite hero in bullets"),
        "AI Tone of Voice": ("🟡", "Mixed (first‑person + promo)", "Rewrite in third‑person expert voice",
            "Neutral expert tone increases trust and likelihood of citation by AI systems.",
            "Rewrite key pages as if an independent expert is recommending you; avoid hype.", "Rewrite About + Services"),
        "Service‑in‑City Pages": ("🔴", "Missing dedicated pages", f"Create location pages (e.g., ‘{geo_example}’)",
            "Dedicated service+city pages feed AI with precise local answers and intent signals.",
            "For each suburb/city: 2 short paragraphs, 1 local testimonial, contact CTA, and LocalBusiness + FAQ schema.",
            "Draft 3 suburb pages and link in footer"),
        "FAQ Depth": ("🟡", "A few basic FAQs", "Add 5–10 buyer FAQs with concise answers",
            "Q&A blocks map directly to how users ask AI and power rich answers.",
            "Add pricing/turnaround/warranty/service‑area FAQs; add FAQPage schema.", "Add 5 FAQs to a top service page"),
        "Testimonials & Case Studies": ("🔴", "Weak social proof", "Create testimonials page and 1–2 case studies",
            "Social proof is a strong recommendation signal for AI and a conversion driver for humans.",
            "Collect 6–10 quotes with names/suburbs; add a ‘Results’ story with before/after.", "Email last 10 customers for quotes"),
        "Comparison Table": ("🔴", "No competitor comparison", "Add a simple comparison table (You vs 3 competitors)",
            "Side‑by‑side comparisons are frequently quoted in AI ‘X vs Y’.",
            "4 columns: You vs 3 competitors; rows: features, warranty, response time, price band, reviews.",
            "Publish /compare with 5 key rows"),
        "Pricing Transparency": ("🟡", "‘Contact us’ only", "Add ‘from’ pricing or ranges",
            "Price signals help AI route high‑intent users and reduce friction.",
            "Publish ‘from’ pricing or typical ranges; link to a pricing explainer.", "Add a 3‑tier pricing block"),
        "Local & Directory Profiles": ("🟡", "Partially completed profiles", f"Complete {dir_examples} and keep NAP consistent",
            "Consistent profiles and citations strengthen local entity understanding for AI and maps.",
            "Ensure name‑address‑phone matches everywhere; add categories, services, photos, hours.",
            "Verify Google Business Profile and add 5 photos"),
        "Reviews Quantity & Rating": ("🟡", "Low review volume", f"Increase {review_focus}; ask after completed jobs",
            "Review volume and recency heavily influence AI recommendations.",
            "Automate review requests by SMS/email post‑job; add Review schema.", "Send review request to last 20 customers"),
        "Press / ‘Best Of’ Mentions": ("🔴", "No third‑party mentions", f"Pitch inclusion in {press_note}",
            "Third‑party mentions validate authority; AI tools lean on them to avoid bias.",
            "Pitch bloggers/journalists; publish ‘Best of [Category] in [City]’ with clear criteria.", "Write a press release about a win"),
        "Technical Markup (Schema)": ("🟡", "Partial schema present", "Add/validate LocalBusiness, FAQPage, Review schema",
            "Structured data helps AI understand entities, services, and proof.",
            "Use JSON‑LD; test in Rich Results & Schema validators; add sameAs links.", "Add FAQPage schema to top page"),
        "Mobile UX & Speed": ("🟢", "Passable mobile UX", "Tidy tap targets; keep CLS/LCP in check",
            "Most AI‑driven searches happen on mobile; poor UX kills conversions.",
            "Ensure click‑to‑call are 1‑tap; compress images; lazy‑load below the fold.", "Compress hero images, verify LCP < 2.5s"),
    }

    # Try to fetch live pages and override the baseline with detected signals
    try:
        fetched = fetch_site(url)
        soups = [BeautifulSoup(h, "html.parser") for h in fetched.values()] if fetched else []
        page_texts = [s.get_text(" ") for s in soups]

        # Readability (pick page with most text or fallback)
        if page_texts:
            longest_idx = max(range(len(page_texts)), key=lambda i: len(page_texts[i]))
            grade = _reading_grade_estimate(page_texts[longest_idx])
        else:
            grade = 10.0

        if grade <= 8:
            data["Home Page Readability"] = ("🟢", f"Clear (Grade ~{grade})", "Keep concise structure",
                "AI prefers succinct, scannable copy.", "Maintain short sentences, bullets, descriptive headings.",
                "Keep hero to 2 lines + 3 bullets")
        elif grade <= 10:
            data["Home Page Readability"] = ("🟡", f"Moderate (Grade ~{grade})", "Tighten copy; shorten sentences",
                "Easier reading improves chance of being quoted.", "Trim long sentences; add bullets to key benefits.",
                "Rewrite hero + first section")
        else:
            data["Home Page Readability"] = ("🔴", f"Complex (Grade ~{grade})", "Simplify to ~7th grade",
                "Complex text won’t be quoted by AI assistants.", "Shorten sentences, swap jargon for plain language.",
                "Rewrite hero + top 2 sections")

        # Tone
        if page_texts:
            tones = [_third_person_signal(t) for t in page_texts]
            if tones.count("third") > len(tones) / 2:
                data["AI Tone of Voice"] = ("🟢", "Third-person", "Maintain expert voice",
                    "Neutral, expert tone increases trust and citations.", "Keep ‘independent expert’ voice; avoid hype.",
                    "Review About + Services for consistency")
            elif tones.count("first") > len(tones) / 2:
                data["AI Tone of Voice"] = ("🔴", "First-person heavy", "Rewrite to third-person expert",
                    "Objective tone is preferred in AI answers.", "Rewrite key pages to expert third-person; reduce ‘we/our’.",
                    "Rewrite About + Services first")
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
            data["FAQ Depth"] = ("🔴", "No proper FAQs", "Add 5–10 buyer FAQs",
                "Directly fuels answer engines and rich results.", "Write concise Q&As; implement FAQPage schema.",
                "Publish 5 FAQs this week")

        # Testimonials
        tcount = sum(_testimonial_score(s) for s in soups) if soups else 0
        if tcount >= 8:
            data["Testimonials & Case Studies"] = ("🟢", "Strong", "Keep fresh & detailed",
                "Social proof boosts AI recommendations and conversions.", "Rotate new quotes and add case studies.",
                "Collect 2 fresh quotes monthly")
        elif tcount >= 3:
            data["Testimonials & Case Studies"] = ("🟡", "Some quotes", "Add more + 1–2 case studies",
                "Proof of outcomes increases trust signals.", "Gather 6–10 quotes; add one before/after story.",
                "Request quotes from last 10 clients")
        else:
            data["Testimonials & Case Studies"] = ("🔴", "Missing/weak", "Create testimonials page + case study",
                "AI and users rely on proof points.", "Collect 6–10 quotes; publish one detailed case study.",
                "Email last 10 customers for a 2‑line quote")

        # Comparison table
        any_compare = any(_has_comparison_table(s) for s in soups) if soups else False
        if any_compare:
            data["Comparison Table"] = ("🟢", "Present", "Ensure clarity & fairness",
                "Side‑by‑side tables are cited in AI ‘X vs Y’.", "Keep factual; add features, warranty, price range.",
                "Add a row for response time")
        else:
            data["Comparison Table"] = ("🔴", "Not found", "Add You vs 3 competitors table",
                "Helps AI for ‘Which is best?’ queries.", "Create a 4‑column table with honest comparisons.",
                "Publish /compare with 5 key rows")

    except Exception:
        # If fetch fails, baseline remains
        pass

    return data

# ---------------------------------
# Premium PDF with Exec Summary + Action Plan
# ---------------------------------
def _score_summary(audit_data: dict):
    SCORE_MAP = {"🟢": 2, "🟡": 1, "🔴": 0}
    total = sum(SCORE_MAP.get(t[0], 0) for t in audit_data.values())
    max_total = 2 * len(audit_data)
    pct = int(round((total / max_total) * 100)) if max_total else 0
    return pct

def _collect_lists(audit_data: dict):
    strengths, weaknesses, qw = [], [], []
    for k, (icon, result, rec, why, how, qwin) in audit_data.items():
        if icon == "🟢":
            strengths.append(f"{k}: {result}")
        else:
            weaknesses.append(f"{k}: {result} — {rec}")
            if qwin: qw.append(qwin)
    # de-dup qw
    seen, out = set(), []
    for q in qw:
        if q not in seen:
            out.append(q); seen.add(q)
    return strengths[:6], weaknesses[:6], out[:6]

if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1024:
    with open(pdf_path, "rb") as f:
        st.download_button("📄 Download Action Plan PDF", f,
                           file_name=os.path.basename(pdf_path), mime="application/pdf")
else:
    st.error("PDF looks empty. Try again or check logs.")

