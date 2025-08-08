
import streamlit as st
from aeo_logic import run_audit, generate_pdf_report
import os, tempfile, traceback

def run_app():
    st.set_page_config(page_title="AEO Audit Tool", layout="centered")
    st.title("🔍 AI SEO (AEO) Audit Tool — Pro (Lite)")
    st.caption("Real site fetch + detectors + premium-ish PDF. If anything breaks, we can fall back to Safe Mode.")

    url = st.text_input("Enter your website URL", placeholder="https://example.com")
    col1, col2 = st.columns(2)
    with col1:
        include_logo = st.checkbox("Include logo (reviewmatebanner.png)", value=os.path.exists("reviewmatebanner.png"))
    with col2:
        contact_email = st.text_input("Contact email in PDF", value="carmine@internetangels.com.au")

    local_mode = st.checkbox("Optimise for Local AU Business", value=True)

    if st.button("🚀 Run Audit", type="primary"):
        if not url:
            st.warning("Please enter a URL first.")
            st.stop()
        try:
            with st.spinner("Fetching key pages and analysing..."):
                audit_results = run_audit(url, local_mode=local_mode)

            st.success("Audit complete.")
            st.subheader("Highlights")
            for area, tup in list(audit_results.items())[:5]:
                icon, result, rec, *_ = tup
                st.markdown(f"**{icon} {area}** — {result}. _{rec}_")

            with st.expander("Full Findings", expanded=False):
                for area, tup in audit_results.items():
                    icon, result, rec, why, how, qwin = tup
                    st.markdown(f"### {icon} {area}")
                    st.markdown(f"**Result:** {result}")
                    st.markdown(f"**Recommendation:** {rec}")
                    st.markdown(f"**Why it matters:** {why}")
                    st.markdown(f"**What to do:** {how}")
                    if qwin:
                        st.markdown(f"**Quick win:** {qwin}")
                    st.markdown("---")

            filename_safe = url.replace("https://", "").replace("http://", "").replace("/", "_")
            output_path = os.path.join(tempfile.gettempdir(), f"AEO_Audit_{filename_safe}.pdf")
            logo_path = "reviewmatebanner.png" if include_logo and os.path.exists("reviewmatebanner.png") else None

            pdf_path = generate_pdf_report(
                audit_data=audit_results,
                output_path=output_path,
                logo_path=logo_path,
                contact_email=contact_email,
                site_url=url
            )

            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 2048:
                with open(pdf_path, "rb") as f:
                    st.download_button("📄 Download Action Plan PDF", data=f, file_name=os.path.basename(pdf_path), mime="application/pdf")
            else:
                st.error("PDF looks empty or too small. Check logs or try again.")

        except Exception:
            st.error("Something went wrong.")
            st.code(traceback.format_exc())

if __name__ == "__main__":
    run_app()
