
import streamlit as st
from aeo_logic import run_audit, generate_pdf_report

def run_app():
    st.title("AI SEO Audit Tool")
    url = st.text_input("Enter a website URL")
    if st.button("Run Audit") and url:
        audit_results = run_audit(url)
        st.write(audit_results)
        pdf_file = generate_pdf_report(url, audit_results)
        with open(pdf_file, "rb") as f:
            st.download_button("Download PDF Report", f, file_name=pdf_file)

if __name__ == "__main__":
    run_app()
