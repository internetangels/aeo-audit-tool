
import streamlit as st
from aeo_logic import run_audit, generate_pdf_report
import os, tempfile, traceback

def run_app():
    st.set_page_config(page_title="AEO Audit Tool (Safe Mode)", layout="centered")
    st.title("AI SEO (AEO) Audit Tool — Safe Mode")
    st.caption("This minimal build is to get you running. Once stable, we can re-enable live fetch and advanced PDF.")

    url = st.text_input("Enter your website URL", placeholder="https://example.com")
    contact_email = st.text_input("Contact email in PDF", value="carmine@internetangels.com.au")

    if st.button("Run Audit", type="primary"):
        if not url:
            st.warning("Please enter a URL first.")
            st.stop()
        try:
            audit_results = run_audit(url, local_mode=True)
            st.success("Audit complete.")

            st.subheader("Findings")
            for area, tup in audit_results.items():
                icon, result, rec, *_ = tup
                st.markdown(f"**{area}** — {icon}: {result}. _{rec}_")

            filename_safe = url.replace("https://", "").replace("http://", "").replace("/", "_")
            output_path = os.path.join(tempfile.gettempdir(), f"AEO_Audit_{filename_safe}.pdf")
            pdf_path = generate_pdf_report(audit_results, output_path, site_url=url, contact_email=contact_email)

            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1024:
                with open(pdf_path, "rb") as f:
                    st.download_button("Download PDF", data=f, file_name=os.path.basename(pdf_path), mime="application/pdf")
            else:
                st.error("PDF was not created or looks too small.")

        except Exception:
            st.error("Unexpected error while running the audit.")
            st.code(traceback.format_exc())

if __name__ == "__main__":
    run_app()
