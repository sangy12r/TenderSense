import streamlit as st
import pdfplumber
import os
import json
from openai import OpenAI
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(layout="wide")

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

# -------------------------------------------------------
# Constants
# -------------------------------------------------------
FREE_CHECKS_LIMIT    = 1
RAZORPAY_LINK        = "https://razorpay.me/@sangeetaailabs"
PRICE_DISPLAY        = "₹49"

WHATSAPP_NUMBER      = "918692859069"
SUPPORT_EMAIL        = "sangy12r@gmail.com"
FEEDBACK_EMAIL       = "sangy12r@gmail.com"

VALID_UNLOCK_CODES = {
    "TSENSE2024A", "TSENSE2024B", "TSENSE2024C", "TSENSE2024D", "TSENSE2024E",
    "TSENSE2025A", "TSENSE2025B", "TSENSE2025C", "TSENSE2025D", "TSENSE2025E",
    "TSENSE2025F", "TSENSE2025G", "TSENSE2025H", "TSENSE2025J", "TSENSE2025K",
    "TSENSE2025L", "TSENSE2025M", "TSENSE2025N", "TSENSE2025P", "TSENSE2025Q",
}

# -------------------------------------------------------
# Session state initialisation
# -------------------------------------------------------
if "free_checks_used"   not in st.session_state:
    st.session_state.free_checks_used  = 0
if "paid_checks"        not in st.session_state:
    st.session_state.paid_checks       = 0
if "used_codes"         not in st.session_state:
    st.session_state.used_codes        = set()
if "analysis_result"    not in st.session_state:
    st.session_state.analysis_result   = None

# NEW — Step flow
if "step"               not in st.session_state:
    st.session_state.step              = 1   # 1 = Understand, 2 = Eligibility
if "tender_summary"     not in st.session_state:
    st.session_state.tender_summary    = None
if "tender_text_cached" not in st.session_state:
    st.session_state.tender_text_cached = None
if "chat_history"       not in st.session_state:
    st.session_state.chat_history      = []  # list of {"role": ..., "content": ...}

# -------------------------------------------------------
# Helper functions
# -------------------------------------------------------
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
    return content.strip()


def check_file_size(uploaded_file, max_size_mb=10):
    if uploaded_file is not None:
        file_size = uploaded_file.size / (1024 * 1024)
        if file_size > max_size_mb:
            st.error(f"File too large. Please upload a file under {max_size_mb} MB.")
            return False
    return True


def generate_pdf_report(missing, partial, mandatory_requirements, final_decision):
    doc = SimpleDocTemplate("tendersense_report.pdf")
    styles = getSampleStyleSheet()
    elements = []
    try:
        logo = Image("logo.png", width=120, height=50)
        elements.append(logo)
        elements.append(Spacer(1, 10))
    except:
        pass
    elements.append(Paragraph("TenderSense Evaluation Report", styles["Title"]))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"<b>Final Decision:</b> {final_decision}", styles["Normal"]))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("<b>Missing Requirements:</b>", styles["Normal"]))
    for item in missing:
        elements.append(Paragraph(f"- {item}", styles["Normal"]))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("<b>Partially Met:</b>", styles["Normal"]))
    for item in partial:
        elements.append(Paragraph(f"- {item}", styles["Normal"]))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("<b>All Requirements:</b>", styles["Normal"]))
    for item in mandatory_requirements:
        elements.append(Paragraph(f"- {item}", styles["Normal"]))
    doc.build(elements)
    return "tendersense_report.pdf"


def user_can_run():
    if st.session_state.free_checks_used < FREE_CHECKS_LIMIT:
        return True
    if st.session_state.paid_checks > 0:
        return True
    return False


def consume_check():
    if st.session_state.free_checks_used < FREE_CHECKS_LIMIT:
        st.session_state.free_checks_used += 1
    else:
        st.session_state.paid_checks -= 1


def is_unlocked():
    return user_can_run() or st.session_state.paid_checks > 0


# -------------------------------------------------------
# App header
# -------------------------------------------------------
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
    st.info("📑 Understand the Tender")
with col2:
    st.info("🔍 Evaluate Company Fit")
with col3:
    st.info("✅ Get Bid Decision")

st.markdown("---")

# -------------------------------------------------------
# Check balance display
# -------------------------------------------------------
free_remaining = max(0, FREE_CHECKS_LIMIT - st.session_state.free_checks_used)
paid_remaining = st.session_state.paid_checks

if free_remaining > 0:
    st.success(f"✅ You have **{free_remaining} free check** remaining.")
elif paid_remaining > 0:
    st.info(f"💳 You have **{paid_remaining} paid check(s)** remaining.")
else:
    st.warning(f"⚠️ Your free check has been used. Pay {PRICE_DISPLAY} to unlock another check.")

# -------------------------------------------------------
# Unlock code entry (shown after free check is used)
# -------------------------------------------------------
if not user_can_run():
    st.markdown("---")
    st.markdown("### 💳 Pay to Run Another Check")
    st.markdown("""
- ✅ Complete eligibility analysis
- ❌ Missing requirements
- ⚠️ Partially met requirements
- 🎯 Final GO / NO-GO decision
- 📄 Downloadable branded PDF report
    """)
    st.caption("🔒 Secure payment powered by Razorpay")
    st.link_button(f"💳 Pay {PRICE_DISPLAY} Securely", RAZORPAY_LINK)
    st.info("After payment, you will receive a unique unlock code via WhatsApp or email.")

    st.markdown("---")
    st.markdown("### 🔐 Already Paid? Enter Your Unlock Code")
    st.caption("Enter the code you received after payment.")

    unlock_input = st.text_input("Enter Unlock Code", placeholder="e.g. TSENSE2024A")

    if st.button("✅ Apply Code"):
        code = unlock_input.strip().upper()
        if code in VALID_UNLOCK_CODES and code not in st.session_state.used_codes:
            st.session_state.paid_checks += 1
            st.session_state.used_codes.add(code)
            st.success("✅ Code accepted! You can now run your eligibility check.")
            st.rerun()
        elif code in st.session_state.used_codes:
            st.error("❌ This code has already been used.")
        else:
            st.error("❌ Invalid code. Please check and try again.")

st.markdown("---")

# ═══════════════════════════════════════════════════════
# STEP INDICATOR
# ═══════════════════════════════════════════════════════
step_col1, step_col2 = st.columns(2)
with step_col1:
    if st.session_state.step == 1:
        st.markdown("### 🔵 Step 1 — Understand the Tender  ◀ You are here")
    else:
        st.markdown("### ✅ Step 1 — Understand the Tender  (Done)")
with step_col2:
    if st.session_state.step == 2:
        st.markdown("### 🔵 Step 2 — Check Eligibility  ◀ You are here")
    else:
        st.markdown("### ⬜ Step 2 — Check Eligibility")

st.markdown("---")

# ═══════════════════════════════════════════════════════
# STEP 1 — UNDERSTAND THE TENDER
# ═══════════════════════════════════════════════════════
if st.session_state.step == 1:

    st.markdown("### 📄 Step 1 — Upload Tender & Understand It")
    st.caption("Upload the tender PDF. AI will summarise it and answer your questions — before you decide to apply.")

    tender_file_step1 = st.file_uploader("Upload Tender PDF", type="pdf", key="tender_step1")

    if tender_file_step1 and check_file_size(tender_file_step1):

        # Generate summary only once
        if st.session_state.tender_summary is None:
            with st.spinner("Reading tender and generating summary..."):
                tender_text = extract_text(tender_file_step1)
                st.session_state.tender_text_cached = tender_text

                summary_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    temperature=0,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert at summarising government and corporate tenders for MSME business owners in simple, clear language."
                        },
                        {
                            "role": "user",
                            "content": f"""Summarise this tender clearly for a business owner. Use simple language.

Include these sections:
1. 📌 What is this tender about? (1-2 lines)
2. 🏢 Who is the issuing authority?
3. 📅 Important dates (submission deadline, pre-bid meeting if any)
4. 💰 Estimated value / EMD amount (if mentioned)
5. 📋 Key eligibility conditions (brief list)
6. 📦 Scope of work (what the bidder must do)
7. ⚠️ Any important conditions to note

Tender document:
{tender_text[:6000]}
"""
                        }
                    ]
                )
                st.session_state.tender_summary = summary_response.choices[0].message.content
                # Seed chat history with context
                st.session_state.chat_history = [
                    {
                        "role": "system",
                        "content": f"You are a helpful tender advisor. Answer questions about this tender based only on the document provided. If the answer is not in the tender, say so clearly.\n\nTender document:\n{tender_text[:6000]}"
                    }
                ]

        # Display summary
        st.markdown("### 📋 Tender Summary")
        st.markdown(st.session_state.tender_summary)
        st.markdown("---")

        # ── Q&A CHAT ──────────────────────────────────────────
        st.markdown("### 💬 Ask Questions About This Tender")
        st.caption("Ask anything — deadlines, EMD amount, eligibility conditions, scope of work, etc.")

        # Display chat history (skip system message at index 0)
        for msg in st.session_state.chat_history[1:]:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.write(msg["content"])
            elif msg["role"] == "assistant":
                with st.chat_message("assistant"):
                    st.write(msg["content"])

        # Chat input
        user_question = st.chat_input("Type your question about the tender...")

        if user_question:
            # Add user message to history
            st.session_state.chat_history.append({
                "role": "user",
                "content": user_question
            })

            # Get AI answer
            with st.spinner("Thinking..."):
                qa_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    temperature=0,
                    messages=st.session_state.chat_history
                )
                answer = qa_response.choices[0].message.content

            # Add assistant reply to history
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": answer
            })

            st.rerun()

        st.markdown("---")

        # ── PROCEED BUTTON ─────────────────────────────────────
        st.markdown("### Ready to check if your company is eligible?")
        if st.button("✅ Proceed to Eligibility Check →", type="primary"):
            st.session_state.step = 2
            st.rerun()

    else:
        st.info("👆 Upload the tender PDF above to get started.")

# ═══════════════════════════════════════════════════════
# STEP 2 — ELIGIBILITY CHECK
# ═══════════════════════════════════════════════════════
elif st.session_state.step == 2:

    st.markdown("### 🏢 Step 2 — Upload Company Profile & Check Eligibility")
    st.caption("Now upload your company profile PDF to check eligibility against the tender.")

    # Back button
    if st.button("← Back to Tender Summary"):
        st.session_state.step = 1
        st.session_state.analysis_result = None
        st.rerun()

    company_file = st.file_uploader("Upload Company Profile PDF", type="pdf", key="company_step2")
    run_button   = st.button("🚀 Run Eligibility Check", disabled=not user_can_run())

    tender_text = st.session_state.tender_text_cached

    if (
        company_file
        and tender_text
        and check_file_size(company_file)
        and run_button
        and user_can_run()
    ):
        with st.spinner("Analyzing company profile against tender requirements..."):
            company_text = extract_text(company_file)

            # STEP 0: Validate tender document
            validation_response = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0,
                messages=[
                    {
                        "role": "system",
                        "content": "Check if the document is a tender document."
                    },
                    {
                        "role": "user",
                        "content": f"""
Is this a tender document?

Answer only like this:
{{"is_tender": true}} or {{"is_tender": false}}

Document:
{tender_text[:2000]}
"""
                    }
                ]
            )

            validation_text = validation_response.choices[0].message.content

            try:
                validation_json = json.loads(clean_json_response(validation_text))
            except:
                st.error("❌ Could not check the document.")
                st.stop()

            if not validation_json.get("is_tender", False):
                st.error("❌ This is not a valid tender document. Please go back and upload a correct tender PDF.")
                st.stop()

            # STEP 1: Extract Eligibility
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
                requirements_json      = json.loads(extraction_content)
                mandatory_requirements = requirements_json["mandatory_requirements"]
            except:
                st.error("Failed to parse eligibility extraction.")
                st.stop()

            # STEP 2: Evaluate Company
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
                evaluation    = matching_json["evaluation"]
            except:
                st.error("Failed to parse evaluation output.")
                st.write(matching_content)
                st.stop()

            # STEP 3: Determine Decision
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

            was_unlocked = user_can_run()

            st.session_state.analysis_result = {
                "mandatory_requirements": mandatory_requirements,
                "evaluation":             evaluation,
                "missing":                missing,
                "partial":                partial,
                "final_decision":         final_decision,
                "was_unlocked":           was_unlocked,
            }
            consume_check()

    # -------------------------------------------------------
    # DISPLAY RESULTS (from session state)
    # -------------------------------------------------------
    result = st.session_state.analysis_result

    if result:
        mandatory_requirements = result["mandatory_requirements"]
        evaluation             = result["evaluation"]
        missing                = result["missing"]
        partial                = result["partial"]
        final_decision         = result["final_decision"]
        full_unlocked          = result.get("was_unlocked", True)

        st.markdown("---")
        st.markdown("## 📊 Eligibility Evaluation")

        if full_unlocked:
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

            # PDF download
            st.markdown("---")
            pdf_path = generate_pdf_report(missing, partial, mandatory_requirements, final_decision)
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="📥 Download Evaluation Report (PDF)",
                    data=f,
                    file_name="tendersense_report.pdf",
                    mime="application/pdf"
                )

            # EMAIL CAPTURE
            st.markdown("---")
            st.markdown("### 📬 Want to save this report or run more checks?")
            st.caption("Leave your email and we'll send you your report + a special offer.")

            col_email, col_btn = st.columns([3, 1])
            with col_email:
                user_email = st.text_input(
                    "Your email address",
                    placeholder="yourname@company.com",
                    label_visibility="collapsed"
                )
            with col_btn:
                email_submitted = st.button("📨 Notify Me")

            if email_submitted:
                if user_email and "@" in user_email:
                    with open("email_leads.txt", "a") as log:
                        import datetime
                        log.write(f"{datetime.datetime.now()} | {user_email} | {final_decision}\n")
                    st.success("✅ Done! We'll be in touch shortly.")
                else:
                    st.warning("Please enter a valid email address.")

        else:
            # PREVIEW + PAYWALL
            st.markdown("### 🔍 Preview (Limited Results)")
            preview_reqs = mandatory_requirements[:2]
            for req in preview_reqs:
                status = evaluation.get(req, "NO_MATCH")
                st.write(f"• {req} → {status}")

            st.markdown("---")
            st.warning("🔒 Full evaluation locked")
            st.markdown(f"""
Unlock to access:
- ✅ Complete eligibility analysis
- ❌ Missing requirements
- ⚠️ Partially met requirements
- 🎯 Final GO / NO-GO decision
- 📄 Downloadable branded PDF report
            """)
            st.caption("🔒 Secure payment powered by Razorpay")
            st.link_button(f"💳 Pay {PRICE_DISPLAY} Securely", RAZORPAY_LINK)
            st.info("After payment, enter your unlock code above to view the full report.")

# -------------------------------------------------------
# SUPPORT & FEEDBACK FOOTER
# -------------------------------------------------------
st.markdown("---")
st.markdown("### 🤝 Need Help or Want to Share Feedback?")

col_support, col_feedback = st.columns(2)

with col_support:
    st.markdown("#### 💬 Contact Support")
    st.caption("Didn't receive your unlock code? Facing any issue? Reach us directly.")
    whatsapp_url = f"https://wa.me/{918692859069}?text=Hi%2C%20I%20need%20help%20with%20TenderSense%20after%20making%20payment."
    st.link_button("💬 Chat on WhatsApp", whatsapp_url)
    st.markdown(f"Or email us: [{SUPPORT_EMAIL}](mailto:{SUPPORT_EMAIL}?subject=TenderSense%20Support)")

with col_feedback:
    st.markdown("#### 📝 Share Your Feedback")
    st.caption("Help us improve TenderSense. Your feedback matters.")
    feedback_subject = "TenderSense%20Feedback"
    feedback_body    = "Hi%20TenderSense%20Team%2C%0A%0AHere%20is%20my%20feedback%3A%0A%0A"
    st.markdown(f"[📧 Send Feedback via Email](mailto:{FEEDBACK_EMAIL}?subject={feedback_subject}&body={feedback_body})")

    with st.expander("✍️ Quick Feedback (Optional)"):
        rating  = st.select_slider("Rate your experience", options=["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"], value="⭐⭐⭐")
        comment = st.text_area("Any suggestions or comments?", placeholder="Tell us what you think...")
        if st.button("📤 Submit Feedback"):
            if comment.strip():
                feedback_link = (
                    f"mailto:{FEEDBACK_EMAIL}"
                    f"?subject=TenderSense%20Feedback%20-%20{rating.replace(' ', '%20')}"
                    f"&body=Rating%3A%20{rating.replace(' ', '%20')}%0A%0AComment%3A%20{comment.replace(' ', '%20').replace(chr(10), '%0A')}"
                )
                st.success("Thanks for your feedback! Click below to send it.")
                st.markdown(f"[📧 Click to Send Feedback]({feedback_link})")
            else:
                st.warning("Please write a comment before submitting.")

st.markdown("---")
st.caption("TenderSense | AI-powered bid / no-bid decision engine for MSMEs")
