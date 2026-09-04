"""
DoneGuard Lite
--------------
A single-page Streamlit app that helps Agile Release Trains (SAFe) enforce
Built-In Quality by automatically generating a Feature-level Definition of
Done (DoD) checklist, required sign-offs, and draft release notes — powered
by the Groq API (OpenAI-compatible chat completions, free tier, no card
required).

Run with:
    streamlit run app.py
"""

import streamlit as st
from groq import Groq


# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="DoneGuard Lite",
    page_icon="✅",
    layout="centered",
)

st.title("✅ DoneGuard Lite")
st.caption("🛠️ Built with AI: Claude (design & code) + Groq (live inference) — a SAFe Summit Buildathon entry")
st.markdown(
    """
    **DoneGuard Lite** helps Agile Release Trains enforce **Built-In Quality**
    under SAFe. Paste a Feature's description and acceptance criteria below,
    and the app will generate a tailored **Definition of Done checklist**,
    the **required role sign-offs**, and a **draft release note** — so
    nothing quality-related slips through before a Feature is called "done."
    """
)
st.caption("💡 **How it works:** AI reads your Feature → generates a tailored DoD checklist, required sign-offs, and draft release notes, in seconds.")

# One-line framing of the SAFe pain point this tool solves — kept visible
# so reviewers immediately see the "why" before they see the "what."
st.info(
    "🎯 **The pain point:** DoD checklists are usually generic, copy-pasted, "
    "and rarely tailored per Feature — so NFRs like security, accessibility, "
    "and performance quietly get skipped. DoneGuard Lite generates a "
    "**Feature-specific** DoD in seconds, so quality is built in, not "
    "bolted on at the end."
)

# ---------------------------------------------------------------------------
# API key — reads from Streamlit's Secrets so ANY visitor to this URL can
# use the app without entering their own key. You (the app owner) set this
# once in Streamlit Cloud's dashboard: App settings → Secrets, as:
#
#   GROQ_API_KEY = "your-real-key-here"
#
# Falls back to a sidebar input for local development/testing, or if no
# secret has been configured yet.
# ---------------------------------------------------------------------------
api_key = st.secrets.get("GROQ_API_KEY", None)

with st.sidebar:
    if api_key:
        st.success("✅ Running on a shared API key — no setup needed to try the app!")
    else:
        st.header("🔑 Groq API Key")
        api_key = st.text_input(
            "Enter your Groq API key",
            type="password",
            help="Your key is used only for this session and is never stored.",
        )
        st.caption(
            "Don't have a key? Get a free one (no credit card) at "
            "[console.groq.com/keys](https://console.groq.com/keys)."
        )

# ---------------------------------------------------------------------------
# Main screen — user input
# ---------------------------------------------------------------------------
st.subheader("Feature Details")

# A ready-made example so reviewers/judges can test the app in one click,
# without needing to write or paste their own Feature description.
SAMPLE_FEATURE = """\
Feature: Allow customers to reset their password via email.

Acceptance Criteria:
1. User can request a password reset link from the login page by entering their registered email.
2. The reset link is sent via email and expires after 30 minutes.
3. Clicking an expired link shows a clear error and offers to resend.
4. New password must meet complexity rules (min 8 characters, 1 number, 1 symbol).
5. User receives a confirmation email once the password has been successfully changed.
6. All password reset attempts are logged for audit purposes.
"""

# Initialize the text area's session state once, so the sample-fill button
# can update it and have the change reflected in the widget below.
if "feature_text" not in st.session_state:
    st.session_state["feature_text"] = ""

def _load_sample():
    st.session_state["feature_text"] = SAMPLE_FEATURE

st.button("📋 Try a sample Feature", on_click=_load_sample)

feature_text = st.text_area(
    "Paste the Feature Description and Acceptance Criteria",
    height=250,
    placeholder=(
        "e.g. Feature: Allow customers to reset their password via email.\n"
        "Acceptance Criteria:\n"
        "1. User can request a reset link from the login page.\n"
        "2. Reset link expires after 30 minutes.\n"
        "3. Password must meet complexity rules.\n"
        "..."
    ),
    key="feature_text",
)

generate_clicked = st.button("Generate Definition of Done", type="primary")

# Simple per-browser-session usage cap. Since this app now runs on a single
# shared API key (see above), this protects Groq's free-tier rate limits
# from being exhausted by one person spamming the button, while still
# giving each peer plenty of room to try the tool out.
MAX_GENERATIONS_PER_SESSION = 8
if "generation_count" not in st.session_state:
    st.session_state["generation_count"] = 0

# ---------------------------------------------------------------------------
# System prompt — instructs the model on exactly what to produce
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
You are an expert SAFe (Scaled Agile Framework) Release Train Engineer and
Quality Coach. Analyze the Feature's description and acceptance criteria,
then produce a CONCISE, SCANNABLE response — a busy RTE or judge should be
able to read the whole thing in under a minute. Prefer short phrases over
full sentences in checklist/list items. Do not restate the Feature text
back to the user.

Respond with EXACTLY three sections, using these Markdown headings verbatim:

## 1. Dynamic DoD Checklist
Markdown checkboxes ("- [ ] item"), max 8 items total, covering BOTH:
  - Technical / functional requirements specific to this Feature (max 4
    items — e.g. code complete, tests passing, code reviewed).
  - Non-Functional Requirements (NFRs) genuinely relevant to THIS Feature
    (max 4 items — choose only from security, accessibility, performance,
    data privacy, observability, scalability; skip any that don't apply).
  Keep each item to a single short line — no sub-explanations.

## 2. Required Sign-offs
Max 4 bullet points. Format each as "**Role** — one short reason (≤10 words)".
Only include roles that are genuinely relevant to this specific Feature.

## 3. Draft Release Notes
2-3 sentences max. Business-friendly, no jargon, no bullet points.

Be specific to the Feature given — never generic or boilerplate. If the
Feature text is vague, make reasonable assumptions and note them in ONE
short line at the end under "### Assumptions" (omit this section entirely
if no assumptions were needed).
"""


# ---------------------------------------------------------------------------
# Logic — validate input and call the Groq API
# ---------------------------------------------------------------------------
if generate_clicked:
    if not api_key:
        st.warning("⚠️ Please enter your Groq API key in the sidebar first.")
    elif not feature_text.strip():
        st.warning("⚠️ Please paste a Feature description before generating.")
    elif st.session_state["generation_count"] >= MAX_GENERATIONS_PER_SESSION:
        st.warning(
            f"⚠️ You've reached the {MAX_GENERATIONS_PER_SESSION}-generation limit "
            "for this session (this keeps the shared demo key available for "
            "everyone). Refresh the page to reset, or use your own free Groq "
            "key in the sidebar for unlimited use."
        )
    else:
        try:
            client = Groq(api_key=api_key)

            with st.spinner("Analyzing Feature and generating compliance requirements..."):
                response = client.chat.completions.create(
                    model="openai/gpt-oss-120b",  # Groq's free-tier flagship model; swap for a lighter/faster model if you hit rate limits
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": feature_text},
                    ],
                    temperature=0.4,
                )

            result_text = response.choices[0].message.content
            st.session_state["generation_count"] += 1

            st.success("Definition of Done generated successfully!")
            st.markdown("---")
            st.markdown(result_text)

        except Exception as e:
            # Catches invalid API keys, network issues, rate limits, etc.
            st.error(f"❌ Something went wrong while calling the Groq API:\n\n{e}")
