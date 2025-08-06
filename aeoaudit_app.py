
import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime
import tempfile

def fetch_page_data(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        return {"error": str(e)}
    
    soup = BeautifulSoup(response.text, 'html.parser')
    title = soup.title.string.strip() if soup.title else None
    meta_desc_tag = soup.find('meta', attrs={"name": "description"})
    meta_desc = meta_desc_tag["content"].strip() if meta_desc_tag and "content" in meta_desc_tag.attrs else None
    h1_tag = soup.find('h1')
    h1 = h1_tag.text.strip() if h1_tag else None
    schema_scripts = soup.find_all('script', type='application/ld+json')
    schema_data = [script.string for script in schema_scripts if script.string]
    schema_found = bool(schema_data)
    potential_qa = bool(soup.find_all(string=re.compile(r'^(what|how|why|when)', re.I)))

    return {
        "Title Tag": bool(title),
        "Meta Description": bool(meta_desc),
        "H1": bool(h1),
        "Schema Markup Found": schema_found,
        "FAQ/Q&A Content Present": potential_qa
    }

def calculate_score(results):
    total = len(results)
    passed = sum(1 for passed in results.values() if passed)
    return int((passed / total) * 100)

def generate_recommendations(results):
    recs = []
    if not results["Title Tag"]:
        recs.append("Add a clear, benefit-driven <title> tag for AI to understand your page.")
    if not results["Meta Description"]:
        recs.append("Include a concise <meta description> in answer format.")
    if not results["H1"]:
        recs.append("Add an <H1> heading that clearly describes your main service.")
    if not results["Schema Markup Found"]:
        recs.append("Add structured data (FAQ, LocalBusiness) to help AI index your content.")
    if not results["FAQ/Q&A Content Present"]:
        recs.append("Include Q&A style content to target AI answers and voice search.")
    return recs

def generate_detailed_pdf_report(url, score, results, recommendations):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        c = canvas.Canvas(tmp_file.name, pagesize=A4)
        width, height = A4
        y = height - 50

        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(width / 2, y, "AI Search Optimization Audit Report")
        y -= 40
        c.setFont("Helvetica", 12)
        c.drawCentredString(width / 2, y, f"Website Audited: {url}")
        y -= 20
        c.drawCentredString(width / 2, y, f"Date: {datetime.today().strftime('%B %d, %Y')}")
        y -= 40
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width / 2, y, f"AEO Readiness Score: {score}%")
        c.showPage()

        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, "Executive Summary")
        c.setFont("Helvetica", 11)
        summary = (
            "AI-powered search engines like ChatGPT, Perplexity, and Google SGE prioritize content "
            "that answers user questions in a structured format. This report shows how well your site "
            "performs and what to fix to appear in AI search answers."
        )
        for line in summary.split('. '):
            y = y - 20
            c.drawString(50, y, line.strip() + '.')
        y -= 40
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "Audit Focus Areas:")
        c.setFont("Helvetica", 11)
        for item in [
            "- Title & Meta evaluation",
            "- Schema markup presence",
            "- Q&A structure for voice/AI",
            "- Actionable steps for improvement"
        ]:
            c.drawString(60, y := y - 20, item)
        c.showPage()

        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, height - 50, "Detailed Audit Results")
        results_table = [
            ["Check", "Result", "Why It Matters"],
            ["Title Tag", "✅" if results["Title Tag"] else "❌", "Appears in search previews"],
            ["Meta Description", "✅" if results["Meta Description"] else "❌", "Helps AI summarize your page"],
            ["H1 Tag", "✅" if results["H1"] else "❌", "Used to identify page purpose"],
            ["Schema Markup", "✅" if results["Schema Markup Found"] else "❌", "Enables rich snippets in AI"],
            ["Q&A Content", "✅" if results["FAQ/Q&A Content Present"] else "❌", "AI loves clear answers"]
        ]
        y = height - 80
        for row in results_table:
            x = 50
            for col in row:
                c.setFont("Helvetica-Bold" if row == results_table[0] else "Helvetica", 10)
                c.drawString(x, y, col)
                x += 170
            y -= 20
        c.showPage()

        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, "Our Recommendations")
        y = height - 80
        c.setFont("Helvetica", 11)
        if recommendations:
            for rec in recommendations:
                for line in rec.split('. '):
                    c.drawString(60, y, "• " + line.strip() + '.')
                    y -= 20
                    if y < 100:
                        c.showPage()
                        y = height - 50
        else:
            c.drawString(60, y, "Your site is well-optimized for AI search. Great job!")
        c.showPage()

        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, height - 50, "Next Steps")
        c.setFont("Helvetica", 11)
        pitch = (
            "At ReviewMate, we turn your website into an AI-friendly sales machine. From adding FAQ blocks "
            "to implementing advanced schema, we handle it all.\n\n"
            "Book your free consultation or request a fix-up quote today."
        )
        for line in pitch.split('\n'):
            c.drawString(50, y := y - 20, line.strip())
        y -= 40
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "📧 Contact: carmine@internetangels.com.au")
        y -= 20
        c.drawString(50, y, "🌐 Powered by ReviewMate")
        c.save()
        return tmp_file.name
