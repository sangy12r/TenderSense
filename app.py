import streamlit as st
import pdfplumber
import os
import json
from openai import OpenAI
st.set_page_config(
        layout="wide"
)

st.image("logo.png", width=320)

st.markdown("""
<style>
body {
    background-color: #F8FAFC;
}
h1, h2, h3 {
    color: #1E3A8A;
}
.stButton>button {
    background-color: #1E3A8A;
    color: white;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.markdown("""
### AI-powered Tender Eligibility Checker for MSMEs

Evaluate tender eligibility in seconds.
Make faster, smarter bid decisions with AI.  
Make smarter bidding decisions with structured AI evaluation.
""")

st.markdown("""
---

### Problem
MSMEs struggle to interpret lengthy tender documents and assess eligibility before bidding.

### Solution
This AI system extracts mandatory eligibility criteria from a tender and evaluates a company's fit based on explicit evidence in its profile.
""")
col1, col2, col3 = st.columns(3)

with col1:
    st.info("📑 Extract Requirements")

with col2:
    st.info("🔍 Evaluate Company Fit")

with col3:
    st.info("✅ Get Bid Decision")
def extract_text(uploaded_file):
    text = ""
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def clean_json_response(content):
    content = content.strip()
    if content.startswith("```"):
        content = content.replace("```json", "")
        content = content.replace("```", "")
    content = content.strip()
    return content
def check_file_size(uploaded_file, max_size_mb=10):
    if uploaded_file is not None:
        file_size = uploaded_file.size / (1024 * 1024)
        if file_size > max_size_mb:
            st.error(f"File too large. Please upload a file under {max_size_mb} MB.")
            return False
    return True
tender_file = st.file_uploader("Upload Tender PDF", type="pdf")
company_file = st.file_uploader("Upload Company Profile PDF", type="pdf")
run_button = st.button("🚀 Run Eligibility Check")

if (
    tender_file 
    and company_file 
    and check_file_size(tender_file)
    and check_file_size(company_file)
    and run_button
):
    with st.spinner("Analyzing tender and company profile..."):

        tender_text = extract_text(tender_file)
        company_text = extract_text(company_file)

        # ----------------------------
        # STEP 1: Extract Eligibility
        # ----------------------------
        extraction_response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": "You extract only bidder pre-qualification eligibility criteria from tenders."
                },
                {
                    "role": "user",
                    "content": f"""
Extract ONLY pre-qualification eligibility criteria required to qualify for bidding.

Include:
- Mandatory licenses
- Mandatory registrations
- Required certifications
- Minimum years of experience
- Specific project experience
- Financial turnover requirements

Exclude:
- Execution clauses
- Legal liability clauses
- Payment terms
- General contract conditions

Return STRICT JSON:

{{
  "mandatory_requirements": [
    "requirement 1",
    "requirement 2"
  ]
}}

Tender:
{tender_text}
"""
                }
            ]
        )

        extraction_content = clean_json_response(
            extraction_response.choices[0].message.content
        )

        try:
            requirements_json = json.loads(extraction_content)
            mandatory_requirements = requirements_json["mandatory_requirements"]
        except:
            st.error("Failed to parse eligibility extraction.")
            st.write(extraction_content)
            st.stop()

        # ----------------------------
        # STEP 2: Evaluate Company
        # ----------------------------
        matching_response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict eligibility evaluation engine."
                },
                {
                    "role": "user",
                    "content": f"""
Evaluate whether the company satisfies each eligibility requirement.

Rules:
- MATCH if clearly satisfied or strongly supported by evidence.
- PARTIAL if partially satisfied.
- NO_MATCH if not satisfied.
- Do not assume beyond provided company profile.

Return STRICT JSON:

{{
  "evaluation": {{
    "requirement text": "MATCH / PARTIAL / NO_MATCH"
  }}
}}

Eligibility Requirements:
{mandatory_requirements}

Company Profile:
{company_text}
"""
                }
            ]
        )

        matching_content = clean_json_response(
            matching_response.choices[0].message.content
        )

        try:
            matching_json = json.loads(matching_content)
            evaluation = matching_json["evaluation"]
        except:
            st.error("Failed to parse evaluation output.")
            st.write(matching_content)
            st.stop()

        # ----------------------------
        # STEP 3: Determine Decision
        # ----------------------------
        missing = []
        partial = []

        for req in mandatory_requirements:
            status = evaluation.get(req, "NO_MATCH")

            if status == "NO_MATCH":
                missing.append(req)
            elif status == "PARTIAL":
                partial.append(req)

        if len(missing) == 0:
            final_decision = "STRONG GO"
        elif len(missing) <= 2:
            final_decision = "CONDITIONAL GO"
        else:
            final_decision = "NO-GO"

        # ----------------------------
        # DISPLAY RESULTS
        # ----------------------------

        st.markdown("---")
        st.markdown("## Eligibility Evaluation")

        for req in mandatory_requirements:
            status = evaluation.get(req, "NO_MATCH")
            st.write(f"• {req}")
            st.write(f"   → {status}")
            st.write("")

        st.markdown("## Missing Mandatory Requirements")

        if missing:
            for m in missing:
                st.write(f"• {m}")
        else:
            st.write("None")

        st.markdown("## Partially Met Requirements")

        if partial:
            for p in partial:
                st.write(f"• {p}")
        else:
            st.write("None")

        st.markdown("## Final Bid Recommendation")

        if final_decision == "STRONG GO":
            st.success(f"Decision: {final_decision}")
        elif final_decision == "CONDITIONAL GO":
            st.warning(f"Decision: {final_decision}")
        else:
            st.error(f"Decision: {final_decision}")
st.markdown("---")
st.caption("TenderSense | AI-powered bid / no-bid decision engine for MSMEs")
