
import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
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
    score = int((passed / total) * 100)
    return score

def generate_recommendations(results):
    messages = []
    if not results["Title Tag"]:
        messages.append("• Add a clear, benefit-driven <title> tag for AI to understand your page.")
    if not results["Meta Description"]:
        messages.append("• Include a concise <meta description> in answer format.")
    if not results["H1"]:
        messages.append("• Add an <H1> heading that clearly describes your main service.")
    if not results["Schema Markup Found"]:
        messages.append("• Add structured data (FAQ, LocalBusiness) to help AI index your content.")
    if not results["FAQ/Q&A Content Present"]:
        messages.append("• Include Q&A style content to target AI answers and voice search.")
    return messages

def generate_pdf_report(url, score, results, recommendations):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        c = canvas.Canvas(tmp_file.name, pagesize=A4)
        width, height = A4

        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 60, "AI Search Optimization Audit Report")
        c.setFont("Helvetica", 12)
        c.drawString(50, height - 90, f"Website Audited: {url}")

        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, height - 130, f"AEO Readiness Score: {score}%")

        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, height - 170, "Audit Results:")
        y = height - 190
        for check, passed in results.items():
            status = "✅ Pass" if passed else "❌ Fail"
            c.setFont("Helvetica", 11)
            c.drawString(60, y, f"- {check}: {status}")
            y -= 20

        if recommendations:
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y - 10, "Recommendations:")
            y -= 30
            for rec in recommendations:
                c.setFont("Helvetica", 11)
                c.drawString(60, y, rec)
                y -= 20

        c.setFont("Helvetica", 10)
        c.drawString(50, 60, "For professional AI Search Optimization services:")
        c.drawString(50, 45, "Contact: carmine@internetangels.com.au")
        c.drawString(50, 30, "Powered by ReviewMate")
        c.save()

        return tmp_file.name

# Streamlit app layout
def run_app():
    st.set_page_config(page_title="AI Search Optimization Audit", layout="centered")
    st.image("reviewmatebanner.png", use_column_width=True)
    st.title("AI Search Optimization (AEO) Audit Tool")
    st.markdown("ReviewMate helps you check if your website is ready for AI-driven search engines like ChatGPT, Google SGE, and Perplexity.")

    url = st.text_input("🔗 Enter a website URL", "https://example.com")

    if st.button("🚀 Run Audit"):
        with st.spinner("Running full AEO audit..."):
            result = fetch_page_data(url)
            if "error" in result:
                st.error(f"Error: {result['error']}")
            else:
                st.success("✅ Audit Complete")
                score = calculate_score(result)
                st.markdown(f"### 🔍 AEO Readiness Score: **{score}%**")

                st.markdown("### 📊 Audit Breakdown")
                for check, passed in result.items():
                    emoji = "✅" if passed else "❌"
                    st.markdown(f"{emoji} **{check}**")

                recommendations = generate_recommendations(result)
                st.markdown("### 💡 Recommendations")
                if recommendations:
                    for msg in recommendations:
                        st.markdown(msg)
                else:
                    st.success("Your site is well-optimized for AI search. Great work!")

                # Generate PDF and provide download button
                pdf_file = generate_pdf_report(url, score, result, recommendations)
                with open(pdf_file, "rb") as f:
                    st.download_button(label="📥 Download PDF Report",
                                       data=f,
                                       file_name="AEO_Audit_Report.pdf",
                                       mime="application/pdf")

                st.markdown("---")
                st.markdown("💬 Want us to fix this for you? [Contact us](mailto:carmine@internetangels.com.au) for a quote.")

if __name__ == "__main__":
    run_app()
