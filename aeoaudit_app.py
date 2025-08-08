
import streamlit as st
from aeo_logic import run_audit, generate_pdf_report
pdf_path = generate_pdf_report(
    audit_data=audit_results,
    output_path=output_path,
    logo_path=logo_path,
    contact_email=contact_email,
    site_url=url
)

# ✅ Do the size check in the app, not in aeo_logic.py
if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 2048:
    with open(pdf_path, "rb") as f:
        st.download_button(
            label="📄 Download Action Plan PDF",
            data=f,
            file_name=os.path.basename(pdf_path),
            mime="application/pdf",
        )
else:
    st.error("PDF looks empty. Try again or check logs.")

import os, tempfile, traceback

def run_app():
    st.set_page_config(page_title="AEO Audit Tool", layout="centered")
    st.title("🔍 AI SEO (AEO) Audit Tool")
    st.caption("Audit your website for AI-search readiness and download a client-ready Action Plan PDF.")

    url = st.text_input("Enter your website URL", placeholder="https://example.com")
    col1, col2 = st.columns([1,1])
    with col1:
        logo_exists = os.path.exists("reviewmatebanner.png")
        st.checkbox("Include logo in PDF (reviewmatebanner.png)", value=logo_exists, key="use_logo")
    with col2:
        contact_email = st.text_input("Contact email in PDF", value="carmine@internetangels.com.au")

    local_mode = st.checkbox("Optimise for Local Australian Business", value=True)

    if st.button("🚀 Run Audit", type="primary", key="run_with_url") and url:
        with st.spinner("Auditing site and preparing Action Plan..."):
            try:
                audit_results = run_audit(url, local_mode=local_mode)

                st.success("Audit complete!")
                st.subheader("Executive Summary")
                st.write("See PDF for full details. Key items:")

                for area, tup in list(audit_results.items())[:5]:
                    icon, result, rec, why, how, qwin = tup
                    st.markdown(f"**{icon} {area}** — {result}. _{rec}_")

                st.subheader("Full Findings")
                for area, tup in audit_results.items():
                    icon, result, rec, why, how, qwin = tup
                    with st.expander(f"{icon} {area}", expanded=False):
                        st.markdown(f"**Result:** {result}")
                        st.markdown(f"**Recommendation:** {rec}")
                        st.markdown(f"**Why it matters:** {why}")
                        st.markdown(f"**What to do:** {how}")
                        if qwin:
                            st.markdown(f"**Quick win:** {qwin}")

                # PDF to /tmp
                filename_safe = url.replace("https://", "").replace("http://", "").replace("/", "_")
                output_path = os.path.join(tempfile.gettempdir(), f"AEO_Audit_{filename_safe}.pdf")
                logo_path = "reviewmatebanner.png" if (st.session_state.get("use_logo") and logo_exists) else None

                pdf_path = generate_pdf_report(
                    audit_data=audit_results,
                    output_path=output_path,
                    logo_path=logo_path,
                    contact_email=contact_email,
                    site_url=url
                )

                if os.path.exists(pdf_path):
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            label="📄 Download Action Plan PDF",
                            data=f,
                            file_name=os.path.basename(pdf_path),
                            mime="application/pdf",
                        )
                else:
                    st.error("❌ PDF file was not created.")

            except Exception as e:
                st.error("Something went wrong while auditing or generating the PDF.")
                st.code(traceback.format_exc())

    elif st.button("🚀 Run Audit", type="primary", key="run_without_url"):
        st.warning("Please enter a valid URL first.")

if __name__ == "__main__":
    run_app()
