
import streamlit as st
from aeo_logic import run_audit, generate_pdf_report
import os

def run_app():
    st.set_page_config(page_title="AEO Audit Tool", layout="centered")
    st.title("🔍 AI SEO (AEO) Audit Tool")
    st.markdown("Audit your website for AI Search Optimization readiness.")

    url = st.text_input("Enter your website URL:", "https://example.com")

    if st.button("Run Audit"):
        with st.spinner("Running audit..."):
            audit_results = run_audit(url)

            st.success("Audit complete!")

            st.subheader("Audit Results")
            for section, (icon, result, recommendation) in audit_results.items():
                st.markdown(f"### {icon} {section}")
                st.write(f"**Result:** {result}")
                st.write(f"**Recommendation:** {recommendation}")
                st.markdown("---")

            # Generate PDF
            output_path = "aeo_audit_report.pdf"
            pdf_path = generate_pdf_report(
                audit_data=audit_results,
                output_path=output_path,
                logo_path="reviewmatebanner.png",
                contact_email="carmine@internetangels.com.au"
            )

            # Provide download link
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="📄 Download PDF Report",
                    data=f,
                    file_name="AEO_Audit_Report.pdf",
                    mime="application/pdf"
                )

if __name__ == "__main__":
    run_app()
