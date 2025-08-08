
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors
from datetime import datetime
import os

def run_audit(url, local_mode=True):
    return {
        "Home Page Readability": ("GREEN", "Readable", "Keep sentences short",
            "Plain language is easier for AI to quote.", "Use short sentences and bullet lists.", "Trim hero copy"),
        "AI Tone of Voice": ("YELLOW", "Mixed first/third person", "Normalize to third-person expert voice",
            "Expert tone increases trust.", "Rewrite About and Services as if by an independent expert.", "Rewrite About first"),
        "FAQ Depth": ("RED", "Few/no FAQs", "Add 5–10 buyer FAQs with concise answers",
            "Q&A maps to how people ask AI.", "Add pricing, turnaround, service area, warranty, contact FAQs.", "Add 5 FAQs this week"),
        "Technical Markup (Schema)": ("YELLOW", "Partial/missing schema", "Add LocalBusiness and FAQPage JSON-LD",
            "Schema helps AI understand entities.", "Validate in Rich Results test; add sameAs links.", "Add FAQPage schema"),
    }

def generate_pdf_report(audit_data, output_path, logo_path=None,
                        contact_email="carmine@internetangels.com.au", site_url=""):
    styles = getSampleStyleSheet()
    title = ParagraphStyle(name="Title", fontSize=18, spaceAfter=12, alignment=1, textColor=colors.HexColor("#1A73E8"))
    h2 = ParagraphStyle(name="H2", fontSize=14, spaceAfter=6, textColor=colors.black)
    cell = ParagraphStyle(name="Cell", fontSize=10, leading=12)

    elements = []
    elements.append(Paragraph("AI Search (AEO) Audit — Executive Summary", title))
    meta = "Website: %s  •  Date: %s" % (site_url or "N/A", datetime.today().strftime("%d %b %Y"))
    elements.append(Paragraph(meta, cell))
    elements.append(Spacer(1, 8))

    rows = [["Area", "Score", "Result", "Recommendation"]]
    for area, (icon, result, rec, _why, _how, _q) in audit_data.items():
        rows.append([area, icon, result, rec])

    table = Table(rows, colWidths=[140, 60, 160, 160])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1A73E8")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 11),
        ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("BACKGROUND", (0,1), (-1,-1), colors.whitesmoke),
    ]))
    elements.append(table)
    elements.append(PageBreak())
    elements.append(Paragraph("Contact: %s" % contact_email, cell))

    doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=28, leftMargin=28, topMargin=28, bottomMargin=24)
    doc.build(elements)
    return output_path
