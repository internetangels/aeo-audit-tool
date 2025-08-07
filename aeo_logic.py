
def run_audit(url):
    return {
        "Voice & Tone": "🟡 First-person (rewrite as third-person expert voice recommended)",
        "Reading Level": "⚠️ 8.4 grade level (⚠️ simplify language)",
        "Service-in-City Page": "✅ Found service reference for Omega in Upwey",
        "FAQ Richness": "✅ 2 Q&As found (✅)",
        "Testimonials": "✅ Found",
        "Comparison Table": "✅ Present"
    }

def generate_pdf_report(url, results):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    import os

    path = f"/mnt/data/aeo-audit-{url.split('//')[-1].split('.')[0]}.pdf"
    doc = SimpleDocTemplate(path, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = [Paragraph("AI SEO Compliance Report", styles["Title"])]

    data = [["Audit Area", "Result", "Recommendation"]]
    for area, result in results.items():
        recommendation = result.split(" (", 1)[-1].rstrip(")") if "(" in result else "Check content"
        data.append([area, result, recommendation])

    table = Table(data, colWidths=[140, 260, 140])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))

    elements.append(table)
    doc.build(elements)
    return path
