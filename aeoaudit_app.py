# aeoaudit_app.py
import streamlit as st
from aeo_logic import run_audit, generate_pdf_report
import os

def run_app():
    st.set_page_config(page_title="AEO Audit Tool", layout="centered")
    st.title("🔍 AI SEO (AEO) Audit Tool")
    st.caption("Audit your website for AI-search readiness and download a client-ready Action Plan PDF.")

    # ---- Input
    url = st.text_input("Enter your website URL", placeholder="https://example.com")

    col1, col2 = st.columns([1,1])
    with col1:
        logo_exists = os.path.exists("reviewmatebanner.png")
        st.checkbox("Include logo in PDF (reviewmatebanner.png)", value=logo_exists, key="use_logo")

    with col2:
        contact_email = st.text_input("Contact email in PDF", value="carmine@internetangels.com.au")

    # ---- Run
    if st.button("🚀 Run Audit", type="primary") and url:
        with st.spinner("Auditing site and preparing Action Plan..."):
            try:
                audit_results = run_audit(url)  # dict: area -> (icon, result, rec, why, how)

                # ---- Display summary in app
                st.success("Audit complete!")
                st.subheader("Results")
                for area, tup in audit_results.items():
                    icon, result, rec, why, how = tup
                    with st.expander(f"{icon} {area}", expanded=False):
                        st.markdown(f"**Result:** {result}")
                        st.markdown(f"**Recommendation:** {rec}")
                        st.markdown(f"**Why it matters:** {why}")
                        st.markdown(f"**What to do:** {how}")

                # ---- Generate PDF
                filename_safe = url.replace("https://", "").replace("http://", "").replace("/", "_")
                output_path = f"AEO_Audit_{filename_safe}.pdf"
                logo_path = "reviewmatebanner.png" if (st.session_state.get("use_logo") and logo_exists) else None

                pdf_path = generate_pdf_report(
                    audit_data=audit_results,
                    output_path=output_path,
                    logo_path=logo_path,
                    contact_email=contact_email
                )

                # ---- Download
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="📄 Download Action Plan PDF",
                        data=f,
                        file_name=os.path.basename(pdf_path),
                        mime="application/pdf",
                    )

                st.divider()
                st.caption("Tip: attach this PDF to your proposal email. It’s built to sell.")

            except Exception as e:
                st.error("Something went wrong while auditing or generating the PDF.")
                st.exception(e)

    elif st.button("🚀 Run Audit", type="primary"):
        st.warning("Please enter a valid URL first.")

if __name__ == "__main__":
    run_app()
