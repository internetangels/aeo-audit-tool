# aeoaudit_app.py
import streamlit as st
import requests
from bs4 import BeautifulSoup
import re

def fetch_page_data(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        return {"error": str(e)}
    
    soup = BeautifulSoup(response.text, 'html.parser')

    title = soup.title.string.strip() if soup.title else "Not Found"
    meta_desc_tag = soup.find('meta', attrs={"name": "description"})
    meta_desc = meta_desc_tag["content"].strip() if meta_desc_tag and "content" in meta_desc_tag.attrs else "Not Found"
    h1_tag = soup.find('h1')
    h1 = h1_tag.text.strip() if h1_tag else "Not Found"

    schema_scripts = soup.find_all('script', type='application/ld+json')
    schema_data = [script.string for script in schema_scripts if script.string]
    schema_found = "Yes" if schema_data else "No"

    potential_qa = bool(soup.find_all(string=re.compile(r'^(what|how|why|when)', re.I)))

    return {
        "Title Tag": title,
        "Meta Description": meta_desc,
        "H1": h1,
        "Schema Markup Found": schema_found,
        "FAQ/Q&A Content Present": "Yes" if potential_qa else "No"
    }

# Streamlit app layout
def run_app():
    st.set_page_config(page_title="AI Search Optimization Audit", layout="centered")
    st.title("🧠 AI Search Optimization (AEO) Audit Tool")
    st.markdown("Analyze your website’s readiness for AI-powered search engines like ChatGPT, Perplexity, and Google SGE.")

    url = st.text_input("🔗 Enter a website URL", "https://example.com")

    if st.button("🚀 Run Audit"):
        with st.spinner("Auditing the site..."):
            result = fetch_page_data(url)
            if "error" in result:
                st.error(f"Error: {result['error']}")
            else:
                st.success("Audit Complete ✅")
                for check, value in result.items():
                    st.markdown(f"**{check}**: {value}")

if __name__ == "__main__":
    run_app()
