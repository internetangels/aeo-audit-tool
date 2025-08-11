import streamlit as st
from aeo_logic import run_audit, generate_pdf_report
import os, tempfile, traceback, io, csv

# ---------- Helpers ----------
def _score_counts(audit_results):
    greens = sum(1 for v in audit_results.values() if v[0] == "🟢")
    ambers = sum(1 for v in audit_results.values() if v[0] == "🟡")
    reds   = sum(1 for v in audit_results.values() if v[0] == "🔴")
    total  = max(1, len(audit_results))
    score_map = {"🟢": 2, "🟡": 1, "🔴": 0}
    got = sum(score_map.get(v[0], 0) for v in audit_results.values())
    pct = int(round((got / float(2 * total)) * 100))
    return greens, ambers, reds, pct

def _to_csv_bytes(audit_results):
    import io, csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Audit Area", "Score", "Result", "Recommendation", "Why it matters", "What to do", "Quick win"])
    for area, (icon, result, rec, why, how, qwin) in audit_results.items():
        writer.writerow([area, icon, result, rec, why, how, qwin or ""])
    return output.getvalue().encode("utf-8")

# ---------- App ----------
def run_app():
    st.set_page_config(page_title="AEO Audit Tool", layout="centered")
    st.title("🔍 AI SEO (AEO) Audit Tool — Pro (Lite+)")
    st.caption("Traffic-light dashboard, CSV export, and sales-ready PDF with ROI.")

    url = st.text_input("Enter your website URL", placeholder="https://example.com")
    ctop1, ctop2 = st.columns(2)
    with ctop1:
        include_logo = st.checkbox("Include logo (reviewmatebanner.png)", value=os.path.exists("reviewmatebanner.png"))
    with ctop2:
        contact_email = st.text_input("Contact email in PDF", value="carmine@internetangels.com.au")

    local_mode = st.checkbox("Optimise for Local AU Business", value=True)

    # 💰 Sales inputs
    st.markdown("### ROI Inputs")
    c1, c2, c3 = st.columns(3)
    with c1:
        avg_sale_value = st.number_input("Average sale value ($)", min_value=0, value=500, step=50)
    with c2:
        baseline_conv = st.number_input("Baseline conversion rate (%)", min_value=0, max_value=100, value=3, step=1)
    with c3:
        monthly_visitors = st.number_input("Monthly qualified visitors", min_value=0, value=300, step=50)

    if st.button("🚀 Run Audit", type="primary"):
        if not url:
            st.warning("Please enter a URL first.")
            st.stop()
        try:
            with st.spinner("Fetching key pages and analysing…"):
                audit_results = run_audit(url, local_mode=local_mode)

            g, a, r, pct = _score_counts(audit_results)
            st.success("Audit complete.")
            st.subheader("Scorecard")

            mc1, mc2, mc3, mc4 = st.columns([1,1,1,2])
            with mc1: st.metric("🟢 Green", g)
            with mc2: st.metric("🟡 Amber", a)
            with mc3: st.metric("🔴 Red", r)
            with mc4: st.metric("Overall AEO Readiness", f"{pct}%")
            st.progress(min(100, pct) / 100.0)

            # Highlights
            st.subheader("Highlights")
            for area, tup in list(audit_results.items())[:5]:
                icon, result, rec, *_ = tup
                st.markdown(f"**{icon} {area}** — {result}. _{rec}_")

            # Full findings
            with st.expander("Full Findings", expanded=False):
                for area, (icon, result, rec, why, how, qwin) in audit_results.items():
                    st.markdown(f"### {icon} {area}")
                    st.markdown(f"**Result:** {result}")
                    st.markdown(f"**Recommendation:** {rec}")
                    st.markdown(f"**Why it matters:** {why}")
                    st.markdown(f"**What to do:** {how}")
                    if qwin: st.markdown(f"**Quick win:** {qwin}")
                    st.markdown("---")

            # Exports
            filename_safe = url.replace("https://", "").replace("http://", "").replace("/", "_")
            output_path = os.path.join(tempfile.gettempdir(), f"AEO_Audit_{filename_safe}.pdf")
            logo_path = "reviewmatebanner.png" if include_logo and os.path.exists("reviewmatebanner.png") else None

            pdf_path = generate_pdf_report(
                audit_data=audit_results,
                output_path=output_path,
                logo_path=logo_path,
                contact_email=contact_email,
                site_url=url,
                avg_sale_value=avg_sale_value,
                baseline_conv_pct=baseline_conv,
                monthly_visitors=monthly_visitors
            )

            exp1, exp2 = st.columns(2)
            with exp1:
                if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 2048:
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            "📄 Download Action Plan PDF",
                            data=f,
                            file_name=os.path.basename(pdf_path),
                            mime="application/pdf",
                        )
                else:
                    st.error("PDF looks empty or too small. Try again or check logs.")

            with exp2:
                csv_bytes = _to_csv_bytes(audit_results)
                st.download_button(
                    "📊 Download CSV (Findings)",
                    data=csv_bytes,
                    file_name=f"AEO_Audit_{filename_safe}.csv",
                    mime="text/csv",
                )

        except Exception:
            st.error("Something went wrong.")
            st.code(traceback.format_exc())

if __name__ == "__main__":
    run_app()
