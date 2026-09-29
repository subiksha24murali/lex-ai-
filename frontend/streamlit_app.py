"""
LexAI dashboard UI — sidebar-navigated multi-agent interface covering:
Legal Advisor, Complaint Drafting, Document Analysis, Service Navigation,
Scam Check, and a "My LexAI" activity dashboard.

Run with:
    streamlit run frontend/streamlit_app.py
"""
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from streamlit_option_menu import option_menu

st.session_state.setdefault("is_authenticated", False)

from src.agents.checklist_generator import generate_checklist
from src.agents.complaint_drafting import export_complaint_docx, generate_complaint
from src.agents.service_navigation import ServiceNavigationAgent
from src.auth.lawyer_service import (
    add_case_document,
    create_consultation_request,
    create_lawyer_profile,
    get_lawyer_profile,
    get_case_document,
    list_case_documents,
    list_citizen_requests,
    list_lawyer_requests,
    list_lawyers,
    list_messages,
    send_message,
    schedule_appointment,
    update_request_status,
)
from src.auth.service import EmailAlreadyExistsError, authenticate_user, register_user
from src.agents.legal_education import LegalEducationAgent
from src.ocr.document_analysis import analyze_document, ask_about_document
from src.rag.pipeline import LexAIPipeline
from src.scam_detection.analyzer import analyze_message
from src.speech.speech_interface import speak_text, transcribe_audio

# --------------------------------------------------------------------------
# Page config + styling
# --------------------------------------------------------------------------
st.set_page_config(page_title="LexAI — Citizen Legal Access", page_icon="L", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Merriweather:wght@700;900&display=swap');
    @import url('https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css');

    :root {
        --lexai-navy: #0B2545;
        --lexai-indigo: #173B68;
        --lexai-gold: #C9A227;
        --lexai-ink: #1A1A2E;
        --lexai-muted: #667085;
        --lexai-neutral: #F4F7FB;
        --lexai-surface: #FFFFFF;
        --lexai-panel: #F8FAFC;
        --lexai-border: #DFE4EC;
        --text-on-light: #1a1a2e;
        --text-on-dark: #f1f5f9;
    }

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; font-size: 16px; }

    .stApp { background: linear-gradient(180deg, #f6f8fb 0%, #eef3f8 100%); }
    .main .block-container {
        max-width: 1100px; padding: 0 2rem 2rem;
        background: rgba(255,255,255,0.18);
        border: 1px solid var(--lexai-border);
        border-radius: 18px;
        box-shadow: 0 6px 18px rgba(17, 34, 58, 0.04);
    }

    h1, h2, h3, h4, h5 { font-family: 'Merriweather', serif !important; }
    h1 { font-size: 2rem !important; line-height: 1.3 !important; }
    h2 { font-size: 1.45rem !important; margin-top: 2rem !important; }
    h3 { font-size: 1.15rem !important; }

    .lexai-header {
        margin: 0 -2rem 2rem;
        padding: 1.25rem 2rem 1rem;
        background: linear-gradient(90deg, #0F243D 0%, #173B68 100%);
        border: 1px solid rgba(201, 162, 39, 0.25);
        border-radius: 14px 14px 0 0;
        border-bottom: 3px solid var(--lexai-gold);
        box-shadow: 0 2px 10px rgba(11, 37, 69, 0.08);
        color: var(--text-on-dark);
    }
    .lexai-header .lexai-wordmark,
    .lexai-header .lexai-wordmark strong,
    .lexai-header .lexai-tagline {
        color: var(--text-on-dark) !important;
    }
    .lexai-wordmark { display: flex; align-items: center; gap: 0.75rem; }
    .lexai-wordmark i { color: var(--lexai-gold); font-size: 1.75rem; }
    .lexai-wordmark strong { font-family: 'Merriweather', serif; font-size: 1.55rem; letter-spacing: 0.01em; }
    .lexai-tagline { margin: 0.25rem 0 0 2.5rem; font-size: 0.82rem; }

    .lexai-utility-marker { display: none; }
    [data-testid="stVerticalBlock"]:has(.lexai-utility-marker) {
        margin: 0 -2rem 0.75rem; padding: 0.18rem 2rem; min-height: 28px;
        background: linear-gradient(90deg, #0f243d 0%, #173b68 100%);
        border: 1px solid rgba(201, 162, 39, 0.22);
        border-radius: 8px;
        color: var(--text-on-dark);
    }
    [data-testid="stVerticalBlock"]:has(.lexai-utility-marker) [data-testid="stHorizontalBlock"] { align-items: center; gap: 0.35rem; }
    [data-testid="stVerticalBlock"]:has(.lexai-utility-marker),
    [data-testid="stVerticalBlock"]:has(.lexai-utility-marker) .stButton>button,
    [data-testid="stVerticalBlock"]:has(.lexai-utility-marker) .stSelectbox > div,
    [data-testid="stVerticalBlock"]:has(.lexai-utility-marker) .stSelectbox [data-baseweb="select"] > div,
    [data-testid="stVerticalBlock"]:has(.lexai-utility-marker) .stMarkdown,
    [data-testid="stVerticalBlock"]:has(.lexai-utility-marker) label,
    [data-testid="stVerticalBlock"]:has(.lexai-utility-marker) p,
    [data-testid="stVerticalBlock"]:has(.lexai-utility-marker) span {
        color: var(--text-on-dark) !important;
    }
    .lexai-utility-label { color: var(--text-on-dark) !important; font-size: 0.75rem; line-height: 2rem; white-space: nowrap; }
    .lexai-utility-divider { height: 20px; margin: 0.35rem auto; border-left: 1px solid rgba(255,255,255,0.35); }
    .lexai-tricolor { display: flex; width: 30px; height: 18px; margin: 0.35rem auto; border-radius: 2px; overflow: hidden; }
    .lexai-tricolor span { flex: 1; }
    .lexai-tricolor .saffron { background: #ff9933; }
    .lexai-tricolor .white { background: #ffffff; }
    .lexai-tricolor .green { background: #138808; }
    [data-testid="stVerticalBlock"]:has(.lexai-utility-marker) .stButton>button {
        min-height: 22px; height: 22px; padding: 0 0.3rem; border: 1px solid rgba(201, 162, 39, 0.42);
        background: rgba(12, 29, 48, 0.58); border-radius: 6px;
        font-size: 0.72rem; font-weight: 700; color: var(--text-on-dark) !important;
    }
    [data-testid="stVerticalBlock"]:has(.lexai-utility-marker) .stButton>button:hover {
        color: var(--lexai-gold) !important; background: rgba(255,255,255,0.08); border-color: rgba(201, 162, 39, 0.75);
    }
    [data-testid="stVerticalBlock"]:has(.lexai-utility-marker) .stSelectbox > div {
        min-height: 28px; border: 1px solid rgba(201, 162, 39, 0.42) !important; background: rgba(12, 29, 48, 0.58);
    }
    [data-testid="stVerticalBlock"]:has(.lexai-utility-marker) .stSelectbox svg { fill: var(--lexai-gold); }

    .lexai-nav-divider { border-bottom: 1px solid var(--lexai-border); margin: -1rem 0 2rem; }
    .lexai-navbar [data-testid="stHorizontalBlock"] {
        background: linear-gradient(180deg, #12314e 0%, #183f68 100%);
        border: 1px solid rgba(201, 162, 39, 0.20);
        border-radius: 10px; overflow: hidden;
        box-shadow: 0 5px 14px rgba(18, 45, 76, 0.08);
    }
    .lexai-navbar .nav-link,
    .lexai-navbar .nav-item a,
    .lexai-navbar .nav-item button {
        color: var(--text-on-dark) !important;
        font-weight: 700 !important;
        letter-spacing: 0.01em;
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 8px;
        opacity: 1;
    }
    .lexai-navbar .nav-link:hover,
    .lexai-navbar .nav-item a:hover,
    .lexai-navbar .nav-item button:hover {
        color: #ffffff !important;
        background: rgba(255,255,255,0.10) !important;
        border-color: rgba(201, 162, 39, 0.25) !important;
    }
    .lexai-navbar .nav-link-selected,
    .lexai-navbar .nav-item.active a,
    .lexai-navbar .nav-item.active button {
        color: var(--lexai-navy) !important;
        background: linear-gradient(180deg, #f4d37c 0%, #d7ae45 100%) !important;
        border-color: rgba(201, 162, 39, 0.4) !important;
        box-shadow: inset 0 0 0 1px rgba(11, 37, 69, 0.08);
    }

    .lexai-page-header { margin: 0 0 2rem; color: var(--text-on-light); }
    .lexai-page-header h1,
    .lexai-page-header .lexai-page-description,
    .lexai-page-header .lexai-breadcrumb,
    .lexai-page-header .lexai-breadcrumb span,
    .lexai-page-header .lexai-breadcrumb i {
        color: var(--text-on-light) !important;
    }
    .lexai-breadcrumb { font-size: 0.78rem; letter-spacing: 0.03em; margin-bottom: 0.65rem; }
    .lexai-breadcrumb i { color: var(--lexai-gold); margin-right: 0.4rem; }
    .lexai-page-header h1 { margin: 0; padding: 0 0 0.65rem; border-bottom: 1px solid var(--lexai-border); }
    .lexai-page-header h1::after { content: ''; display: block; width: 56px; border-bottom: 3px solid var(--lexai-gold); position: relative; top: 0.8rem; }
    .lexai-page-description { margin: 1rem 0 0; color: var(--text-on-light) !important; }

    .lexai-card {
        background: var(--lexai-surface);
        border: 1px solid var(--lexai-border); border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem;
        box-shadow: 0 4px 16px rgba(11,37,69,0.06); border-left: 4px solid var(--lexai-gold);
        color: var(--text-on-light);
    }
    .lexai-flow-step {
        background: var(--lexai-surface); border: 1px solid var(--lexai-border); border-left: 4px solid var(--lexai-indigo);
        border-radius: 10px; padding: 1.25rem 1.5rem; margin: 0.5rem 0; box-shadow: 0 3px 12px rgba(11,37,69,0.05);
        color: var(--text-on-light);
    }
    .lexai-flow-arrow { text-align: center; color: var(--lexai-gold); font-size: 1rem; margin: 0.25rem 0; }
    .lexai-badge {
        display: inline-block; background: #eef1f5; color: var(--lexai-navy) !important;
        padding: 0.25rem 0.7rem; border-radius: 999px; font-size: 0.76rem; font-weight: 600;
    }
    .lexai-disclaimer {
        background: #fbf8ee; border: 1px solid #e2d5a8; border-radius: 8px;
        padding: 0.75rem 1rem; font-size: 0.82rem; color: var(--lexai-navy) !important; margin-top: 1rem;
    }
    .lexai-action-banner {
        background: linear-gradient(120deg, #0b2545 0%, #1d5277 100%);
        border: 1px solid rgba(201, 162, 39, 0.45); border-radius: 12px;
        padding: 1.4rem 1.5rem; margin-bottom: 1.25rem; color: #ffffff;
    }
    .lexai-action-banner h3, .lexai-action-banner p { color: #ffffff !important; margin-top: 0; }
    .lexai-lawyer-card {
        background: var(--lexai-surface); border: 1px solid var(--lexai-border);
        border-radius: 10px; padding: 1rem 1.1rem; margin-bottom: 0.8rem;
        box-shadow: 0 3px 12px rgba(11,37,69,0.05); color: var(--text-on-light);
    }
    .lexai-lawyer-card h4 { margin: 0 0 0.35rem; color: var(--lexai-navy) !important; }
    .lexai-lawyer-meta { color: var(--lexai-muted); font-size: 0.85rem; line-height: 1.6; }
    .lexai-source-chip {
        display: inline-block; background: #eef1f5; border-radius: 6px;
        padding: 0.3rem 0.6rem; margin: 0.15rem; font-size: 0.76rem; color: var(--text-on-light) !important;
    }
    .lexai-source-label { color: var(--text-on-light) !important; font-size: 0.82rem; font-weight: 600; }

    [data-testid="stToolbar"] { display: none !important; }

    .lexai-auth-shell {
        max-width: 980px;
        margin: clamp(1rem, 4vh, 2.5rem) auto 0;
        background: #ffffff;
        border: 1px solid var(--lexai-border);
        border-radius: 22px;
        box-shadow: 0 18px 42px rgba(11,37,69,0.10);
        overflow: hidden;
    }
    .lexai-auth-shell [data-testid="stVerticalBlock"] { margin: 0; }
    .lexai-auth-shell [data-testid="stColumn"] > div { height: 100%; }

    .lexai-auth-brand {
        background: linear-gradient(180deg, var(--lexai-navy) 0%, var(--lexai-indigo) 100%);
        color: var(--text-on-dark);
        padding: 2.5rem;
        min-height: 100%;
        display: flex;
        align-items: center;
    }
    .lexai-auth-brand .lexai-wordmark,
    .lexai-auth-brand h2,
    .lexai-auth-brand p,
    .lexai-auth-brand .lexai-auth-list,
    .lexai-auth-brand .lexai-auth-list div,
    .lexai-auth-brand .lexai-auth-list i {
        color: var(--text-on-dark) !important;
    }
    .lexai-auth-brand h2 { font-size: 2rem !important; margin: 0 0 0.75rem !important; }
    .lexai-auth-brand p { opacity: 1; margin-bottom: 0; }
    .lexai-auth-brand .lexai-auth-list { margin-top: 1.75rem; }
    .lexai-auth-brand .lexai-auth-list div { margin: 0.75rem 0; }
    .lexai-auth-brand .lexai-auth-list i { color: var(--lexai-gold); margin-right: 0.6rem; }

    .lexai-auth-card {
        background: #ffffff;
        border: none;
        border-radius: 0;
        box-shadow: none;
        padding: 2.5rem;
        min-height: 100%;
        color: var(--text-on-light);
    }
    [data-testid="stTabs"] { margin-top: 0; }
    .stTabs [role="tablist"] {
        display: flex;
        gap: 1.5rem;
        background: transparent;
        border: none;
        border-bottom: 1px solid var(--lexai-border);
        border-radius: 0;
        padding: 0 0 0.5rem;
        margin-bottom: 1.5rem;
    }
    .stTabs [role="tab"] {
        color: var(--lexai-muted) !important;
        background: transparent !important;
        border: none !important;
        border-bottom: 2px solid transparent !important;
        border-radius: 0;
        font-weight: 700;
        padding: 0.45rem 0.2rem;
        margin: 0;
        letter-spacing: 0.01em;
    }
    .stTabs [role="tab"][aria-selected="true"] {
        background: transparent !important;
        color: var(--lexai-navy) !important;
        border-bottom-color: var(--lexai-gold) !important;
    }
    .lexai-auth-card label,
    .lexai-auth-card .stTextInput > label,
    .lexai-auth-card .stForm,
    .lexai-auth-card .stCheckbox,
    .lexai-auth-card .stAlert,
    .lexai-auth-card .stSuccess,
    .lexai-auth-card .stError,
    .lexai-auth-card .stInfo,
    .lexai-auth-card .stTextInput,
    .lexai-auth-card .stMarkdown {
        color: var(--text-on-light) !important;
    }
    .lexai-auth-card input,
    .lexai-auth-card textarea,
    .lexai-auth-card .stTextInput > div,
    .lexai-auth-card .stSelectbox > div {
        background: #ffffff !important;
        color: var(--text-on-light) !important;
        border: 1px solid var(--lexai-border) !important;
        border-radius: 10px !important;
    }
    .lexai-auth-card input:focus,
    .lexai-auth-card textarea:focus { border-color: var(--lexai-gold) !important; box-shadow: 0 0 0 1px var(--lexai-gold) !important; }
    .lexai-auth-card .stButton > button[kind="primary"] {
        background-color: var(--lexai-navy);
        border-color: var(--lexai-navy);
        color: #ffffff !important;
        border-radius: 10px;
        font-weight: 700;
        padding: 0.7rem 1.2rem;
    }

    [data-testid="stStatusWidget"] { background: var(--lexai-surface); border: 1px solid var(--lexai-border); border-left: 4px solid var(--lexai-gold); border-radius: 10px; color: var(--lexai-navy); }
    .lexai-footer { margin: 4rem -2rem 0; padding: 1.5rem 2rem; border-top: 1px solid var(--lexai-border); color: var(--lexai-muted); font-size: 0.75rem; }
    .lexai-footer strong { color: var(--lexai-navy); }
    .lexai-footer i { color: var(--lexai-gold); margin-right: 0.4rem; }

    .stButton>button, .stDownloadButton>button { border-radius: 8px; font-weight: 600; min-height: 42px; padding: 0.5rem 1.3rem; }
    .stButton>button[kind="primary"] {
        background-color: var(--lexai-navy); border-color: var(--lexai-navy); color: #ffffff !important;
    }
    .stButton>button[kind="primary"]:hover {
        background-color: var(--lexai-indigo); border-color: var(--lexai-indigo); color: #ffffff !important;
    }
    .stDownloadButton>button { background: var(--lexai-navy); color: #ffffff !important; border-color: var(--lexai-navy); }

    textarea, input, .stSelectbox > div, .stTextInput > div {
        border-radius: 8px !important;
        border-color: var(--lexai-border) !important;
    }
    textarea:focus, input:focus { border-color: var(--lexai-gold) !important; box-shadow: 0 0 0 1px var(--lexai-gold) !important; }

    [data-testid="stMetric"] {
        background: var(--lexai-surface); border: 1px solid var(--lexai-border); border-radius: 10px; padding: 1rem;
        box-shadow: 0 3px 12px rgba(11,37,69,0.05);
    }
    [data-testid="stMetricLabel"] { color: var(--lexai-muted) !important; }
    [data-testid="stMetricValue"] { color: var(--lexai-navy) !important; font-family: 'Merriweather', serif; }
    @media (max-width: 700px) {
        .main .block-container { padding: 0 1rem 1rem; }
        [data-testid="stVerticalBlock"]:has(.lexai-utility-marker) { margin-left: -1rem; margin-right: -1rem; padding-left: 1rem; padding-right: 1rem; }
        .lexai-header { margin-left: -1rem; margin-right: -1rem; padding-left: 1rem; padding-right: 1rem; }
        .lexai-footer { margin-left: -1rem; margin-right: -1rem; padding-left: 1rem; padding-right: 1rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------
# Cached resources + session state
# --------------------------------------------------------------------------
@st.cache_resource
def get_pipeline():
    return LexAIPipeline()


@st.cache_resource
def get_navigation_agent():
    return ServiceNavigationAgent()


pipeline = get_pipeline()
nav_agent = get_navigation_agent()

for key, default in [
    ("history_questions", []),
    ("history_complaints", []),
    ("history_documents", []),
    ("last_doc_text", None),
    ("last_doc_name", None),
    ("last_legal_answer", None),
    ("last_legal_answer_language", "English"),
    ("lawyer_requests", []),
]:
    st.session_state.setdefault(key, default)

DISCLAIMER = (
    "LexAI provides general educational legal information and is not a "
    "substitute for a qualified lawyer or the relevant official authority."
)

LANGUAGES = ["English", "Hindi", "Tamil"]
LANGUAGE_LABELS = {"English": "English", "Hindi": "हिंदी", "Tamil": "தமிழ்"}
st.session_state.setdefault("global_language", "English")
st.session_state.setdefault("current_user", None)


def render_auth_screen():
    left_col, right_col = st.columns([1.1, 1.3])

    with left_col:
        st.markdown(
            """
            <div class='lexai-auth-brand'>
                <div>
                    <div class='lexai-wordmark' style='margin-bottom: 1.5rem;'><i class='bi bi-bank2'></i><strong>LexAI</strong></div>
                    <h2>Citizen Legal Access</h2>
                    <p>Secure access to official legal guidance, complaint drafting, document review, and service navigation.</p>
                    <div class='lexai-auth-list'>
                        <div><i class='bi bi-shield-check'></i> Trusted legal information</div>
                        <div><i class='bi bi-file-earmark-text'></i> Complaint and document support</div>
                        <div><i class='bi bi-map'></i> Government service guidance</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right_col:
        auth_tab, signup_tab = st.tabs(["Log In", "Sign In"])

        with auth_tab:
            with st.form("login_form"):
                email = st.text_input("Email address")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Log In", type="primary")
                if submitted:
                    user = authenticate_user(email, password)
                    if user is None:
                        st.error("Invalid email or password")
                    else:
                        st.session_state["current_user"] = user
                        st.session_state["is_authenticated"] = True
                        st.success("Login successful.")
                        st.rerun()

        with signup_tab:
            with st.form("signup_form"):
                full_name = st.text_input("Full name")
                email = st.text_input("Email address")
                password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm password", type="password")
                account_role = st.selectbox("Account type", ["citizen", "lawyer"])
                submitted = st.form_submit_button("Create Account", type="primary")
                if submitted:
                    if not full_name or not email or not password:
                        st.error("Please fill in all fields.")
                    elif password != confirm_password:
                        st.error("Passwords do not match.")
                    else:
                        try:
                            register_user(full_name, email, password, role=account_role)
                        except EmailAlreadyExistsError as error:
                            st.error(str(error))
                        else:
                            user = authenticate_user(email, password)
                            st.session_state["current_user"] = user
                            st.session_state["is_authenticated"] = True
                            st.success("Account created successfully.")
                            st.rerun()


# --------------------------------------------------------------------------
# Utility bar, header, and horizontal navigation
# --------------------------------------------------------------------------
if not st.session_state.get("is_authenticated", False):
    st.markdown("<div class='lexai-auth-shell'>", unsafe_allow_html=True)
    render_auth_screen()
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

with st.sidebar:
    current_user = st.session_state.get("current_user")
    if current_user:
        st.write(f"Signed in as {current_user['full_name']}")
    if st.button("Log Out"):
        st.session_state["is_authenticated"] = False
        st.session_state["current_user"] = None
        st.rerun()

with st.container():
    st.markdown("<span class='lexai-utility-marker'></span>", unsafe_allow_html=True)
    utility_left, utility_divider, utility_language, utility_divider_2, utility_flag = st.columns(
        [3.8, 0.18, 1.25, 0.18, 0.5]
    )
    with utility_left:
        st.markdown("<a class='lexai-skip-link' href='#main-content'>Skip to Main Content</a>", unsafe_allow_html=True)
    with utility_divider:
        st.markdown("<div class='lexai-utility-divider'></div>", unsafe_allow_html=True)
    with utility_language:
        st.selectbox(
            "Global language",
            LANGUAGES,
            key="global_language",
            format_func=lambda value: LANGUAGE_LABELS[value],
            label_visibility="collapsed",
        )
    with utility_divider_2:
        st.markdown("<div class='lexai-utility-divider'></div>", unsafe_allow_html=True)
    with utility_flag:
        st.markdown(
            "<div class='lexai-tricolor'><span class='saffron'></span><span class='white'></span><span class='green'></span></div>",
            unsafe_allow_html=True,
        )

st.markdown(
    """<header class='lexai-header'>
    <div class='lexai-wordmark'><i class='bi bi-bank2'></i><strong>LexAI</strong></div>
    <p class='lexai-tagline'>Multilingual legal rights and citizen assistance</p>
    </header>""",
    unsafe_allow_html=True,
)
st.markdown("<div class='lexai-navbar'>", unsafe_allow_html=True)
menu_options = [
    "My LexAI (Dashboard)", "Legal Advisor", "Connect to a Lawyer", "Legal Education",
    "Complaint Drafting", "Document Analysis", "Service Navigation", "📋 Document Checklist", "Scam Check",
]
menu_icons = [
    "house", "briefcase", "person-vcard", "book", "file-earmark-text", "file-earmark-medical",
    "signpost-split", "clipboard-check", "shield-check",
]
if st.session_state.get("current_user", {}).get("role") == "lawyer":
    menu_options.insert(1, "Lawyer Dashboard")
    menu_icons.insert(1, "person-badge")
page = option_menu(
    menu_title=None,
    options=menu_options,
    icons=menu_icons,
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {
            "padding": "0!important",
            "background-color": "#0B2545",
            "border-radius": "8px",
        },
        "icon": {"color": "#C9A227", "font-size": "0.95rem"},
        "nav-link": {
            "font-size": "0.8rem",
            "font-weight": "700",
            "text-align": "center",
            "margin": "0px",
            "padding": "0.9rem 0.7rem",
            "color": "#F1F5F9",
            "background-color": "rgba(255,255,255,0.02)",
            "border": "1px solid rgba(255,255,255,0.04)",
            "border-radius": "8px",
            "--hover-color": "rgba(255,255,255,0.10)",
        },
        "nav-link-selected": {
            "background-color": "#C9A227",
            "color": "#0B2545",
            "border": "1px solid rgba(201, 162, 39, 0.45)",
            "font-weight": "800",
        },
    },
)
st.markdown("</div><div class='lexai-nav-divider'></div>", unsafe_allow_html=True)


def page_header(title, description, icon):
    st.markdown(
        f"""<div class='lexai-page-header'>
        <div class='lexai-breadcrumb'><i class='bi bi-house-door'></i> Home <span>›</span> {title}</div>
        <h1>{icon} {title}</h1>
        <p class='lexai-page-description'>{description}</p>
        </div>""",
        unsafe_allow_html=True,
    )


def render_footer():
    st.markdown(
        """<footer class='lexai-footer'>
        <div><i class='bi bi-telephone'></i><strong>Citizen helpline:</strong> 1800-000-2026</div>
        <div>LexAI — Educational Legal Information Platform</div>
        <div>Information is general and educational. Please consult the relevant official authority or a qualified lawyer.</div>
        </footer>""",
        unsafe_allow_html=True,
    )


def render_sources(sources):
    if not sources:
        return
    chips = "".join(f"<span class='lexai-source-chip'><i class='bi bi-file-earmark-text'></i> {s['source']} · {s['category']}</span>" for s in sources)
    st.markdown(f"<div class='lexai-source-label'>Sources retrieved</div>{chips}", unsafe_allow_html=True)


# --------------------------------------------------------------------------
# PAGE: Dashboard
# --------------------------------------------------------------------------
if page == "My LexAI (Dashboard)":
    page_header("My LexAI", "Your recent activity across all LexAI services in this session.", "<i class='bi bi-grid-1x2'></i>")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Questions Asked", len(st.session_state.history_questions))
    c2.metric("Complaints Drafted", len(st.session_state.history_complaints))
    c3.metric("Documents Analyzed", len(st.session_state.history_documents))
    c4.metric("Lawyer Requests", len(st.session_state.lawyer_requests))

    st.markdown("### Recent Questions")
    if st.session_state.history_questions:
        for item in reversed(st.session_state.history_questions[-5:]):
            st.markdown(
                f"<div class='lexai-card'><span class='lexai-badge'>{item['language']}</span> "
                f"&nbsp; {item['question']}</div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("No questions asked yet — try the Legal Advisor tab.")

    st.markdown("### Recent Complaints")
    if st.session_state.history_complaints:
        for item in reversed(st.session_state.history_complaints[-5:]):
            st.markdown(
                f"<div class='lexai-card'><span class='lexai-badge'>{item.get('complaint_type','')}</span> "
                f"&nbsp; {item.get('issue_summary','')}</div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("No complaints drafted yet — try the Complaint Drafting tab.")

    st.markdown("### Recent Documents")
    if st.session_state.history_documents:
        for item in reversed(st.session_state.history_documents[-5:]):
            st.markdown(
                f"<div class='lexai-card'><span class='lexai-badge'>{item['doc_type']}</span> "
                f"&nbsp; {item['name']}</div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("No documents analyzed yet — try the Document Analysis tab.")

    st.markdown("### Consultation Requests")
    if st.session_state.lawyer_requests:
        for item in reversed(st.session_state.lawyer_requests[-5:]):
            st.markdown(
                f"<div class='lexai-card'><span class='lexai-badge'>{item['practice_area']}</span> "
                f"&nbsp; {item['summary']}<br><small>{item['created_at']}</small></div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("No lawyer consultation requests yet — use Connect to a Lawyer when you need human review.")


# --------------------------------------------------------------------------
# PAGE: Legal Advisor Agent
# --------------------------------------------------------------------------
elif page == "Legal Advisor":
    page_header("Legal Advisor", "Describe your situation and receive grounded, structured legal information.", "<i class='bi bi-journal-text'></i>")

    language = st.selectbox("Language", LANGUAGES, index=LANGUAGES.index(st.session_state["global_language"]))
    question = st.text_area(
        "Describe your situation or question",
        placeholder="e.g. My employer has not paid my salary for two months.",
    )

    st.markdown("#### Ask by voice")
    if hasattr(st, "audio_input"):
        voice_audio = st.audio_input("Record your legal question", key="legal_voice_input")
    else:
        voice_audio = st.file_uploader(
            "Upload a voice question",
            type=["wav", "mp3", "m4a"],
            key="legal_voice_input",
        )

    if st.button("Get Guidance", type="primary") and question.strip():
        with st.status("Retrieving relevant law and drafting a grounded answer...", expanded=False):
            result = pipeline.answer(question, language=language)

        st.session_state["last_legal_answer"] = result["answer"]
        st.session_state["last_legal_answer_language"] = language
        st.markdown(f"<div class='lexai-card'>{result['answer']}</div>", unsafe_allow_html=True)
        render_sources(result["retrieved_sources"])
        st.markdown(f"<div class='lexai-disclaimer'>{DISCLAIMER}</div>", unsafe_allow_html=True)

        st.session_state.history_questions.append(
            {"question": question, "language": language, "time": datetime.now().isoformat()}
        )

    if voice_audio and st.button("Get Guidance from Voice", type="primary"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as audio_file:
            audio_file.write(voice_audio.getvalue())
            audio_path = audio_file.name

        with st.status("Transcribing your question and retrieving legal guidance...", expanded=False):
            transcribed_question = transcribe_audio(audio_path)
            result = pipeline.answer(transcribed_question, language=language)

        st.session_state["last_legal_answer"] = result["answer"]
        st.session_state["last_legal_answer_language"] = language
        st.markdown(f"<div class='lexai-card'><b>Transcribed question:</b> {transcribed_question}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='lexai-card'>{result['answer']}</div>", unsafe_allow_html=True)
        render_sources(result["retrieved_sources"])
        st.markdown(f"<div class='lexai-disclaimer'>{DISCLAIMER}</div>", unsafe_allow_html=True)

        st.session_state.history_questions.append(
            {"question": transcribed_question, "language": language, "time": datetime.now().isoformat()}
        )

    if st.session_state.get("last_legal_answer"):
        if st.button("🔊 Listen to answer", key="listen_to_legal_answer"):
            speech_language = {"English": "en", "Hindi": "hi", "Tamil": "ta"}[st.session_state["last_legal_answer_language"]]
            audio_path = speak_text(st.session_state["last_legal_answer"], speech_language)
            st.audio(audio_path, format="audio/mp3")


# --------------------------------------------------------------------------
# PAGE: Lawyer Connection
# --------------------------------------------------------------------------
elif page == "Connect to a Lawyer":
    page_header(
        "Connect to a Lawyer",
        "Turn your LexAI work into a consultation request that a qualified lawyer can act on.",
        "<i class='bi bi-person-vcard'></i>",
    )
    st.markdown(
        """<div class='lexai-action-banner'>
        <h3>Ready for a human legal review?</h3>
        <p>Choose the kind of help you need, prepare a short case brief, and send a clear request for a consultation.</p>
        </div>""",
        unsafe_allow_html=True,
    )

    practice_areas = [
        "Any practice area", "Family law", "Labour and employment", "Consumer protection",
        "Property law", "Criminal law", "Cybercrime", "Senior citizen rights",
    ]
    languages = ["Any language", "English", "Hindi", "Tamil"]
    area_col, language_col = st.columns(2)
    with area_col:
        selected_area = st.selectbox("What kind of lawyer do you need?", practice_areas, key="lawyer_area")
    with language_col:
        selected_language = st.selectbox("Preferred consultation language", languages, key="lawyer_language")

    registered_lawyers = list_lawyers(selected_area, selected_language)
    if registered_lawyers:
        st.subheader("Registered lawyer profiles")
        for lawyer in registered_lawyers:
            verification_label = "Verified" if lawyer["verification_status"] == "verified" else "Verification pending"
            st.markdown(
                f"<div class='lexai-lawyer-card'><h4>{lawyer['full_name']}</h4>"
                f"<div class='lexai-lawyer-meta'><b>{verification_label}</b><br>"
                f"Practice areas: {lawyer['practice_areas']}<br>Languages: {lawyer['languages']}<br>"
                f"{lawyer['bio']}</div></div>",
                unsafe_allow_html=True,
            )

    lawyer_directory = [
        {
            "name": "Legal Aid Clinic referral",
            "area": "Family law, Labour and employment",
            "languages": "English, Hindi, Tamil",
            "type": "Legal-aid referral",
            "note": "Ask the relevant State Legal Services Authority about eligibility and appointment availability.",
        },
        {
            "name": "District Legal Services Authority",
            "area": "Criminal law, Family law, Consumer protection",
            "languages": "English, Hindi, Tamil",
            "type": "Government legal aid",
            "note": "Use the official district court or NALSA contact channel to request a lawyer appointment.",
        },
        {
            "name": "Independent advocate referral",
            "area": "Property law, Consumer protection, Cybercrime",
            "languages": "English, Hindi",
            "type": "Private consultation",
            "note": "Verify the advocate's Bar Council enrolment, fees, and availability before sharing documents.",
        },
    ]
    matches = [
        lawyer for lawyer in lawyer_directory
        if selected_area == "Any practice area" or selected_area in lawyer["area"]
    ]
    if selected_language != "Any language":
        matches = [lawyer for lawyer in matches if selected_language in lawyer["languages"]]

    st.subheader("Starting points")
    st.caption("These are referral routes, not a claim that a lawyer is currently online or assigned. Confirm identity and availability through an official channel.")
    for index, lawyer in enumerate(matches):
        st.markdown(
            f"""<div class='lexai-lawyer-card'>
            <h4>{lawyer['name']}</h4>
            <div class='lexai-lawyer-meta'><b>{lawyer['type']}</b><br>
            Practice areas: {lawyer['area']}<br>
            Languages: {lawyer['languages']}<br>{lawyer['note']}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    if not matches:
        st.info("No starting point matches both filters. Select Any practice area or Any language to see broader referral routes.")

    st.subheader("Prepare your consultation request")
    with st.form("lawyer_request_form"):
        issue_summary = st.text_input(
            "One-line summary",
            placeholder="e.g. My employer has withheld two months of salary.",
        )
        case_details = st.text_area(
            "What should the lawyer know?",
            placeholder="Share the key facts, dates, people involved, action already taken, and what outcome you want.",
            height=150,
        )
        contact_col, contact_method_col = st.columns(2)
        with contact_col:
            contact_details = st.text_input("Safe contact detail", placeholder="Phone number or email")
        with contact_method_col:
            contact_method = st.selectbox("Preferred contact method", ["Phone", "Email", "Video consultation"])
        consent = st.checkbox("I understand this request may contain sensitive information and I will verify the recipient before sending it.")
        request_submitted = st.form_submit_button("Create consultation request", type="primary")

    if request_submitted:
        if not issue_summary.strip() or not case_details.strip() or not contact_details.strip():
            st.error("Add a summary, key facts, and a safe contact detail before creating the request.")
        elif not consent:
            st.error("Please confirm that you will verify the recipient before sharing sensitive information.")
        else:
            request = {
                "summary": issue_summary.strip(),
                "details": case_details.strip(),
                "contact": contact_details.strip(),
                "contact_method": contact_method,
                "practice_area": selected_area,
                "language": selected_language,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
            request_id = create_consultation_request(
                st.session_state["current_user"]["id"],
                request["summary"],
                request["details"],
                request["practice_area"],
                request["language"],
            )
            request["id"] = request_id
            st.session_state.lawyer_requests.append(request)
            st.session_state["last_lawyer_request"] = request
            st.success("Your consultation request was saved. A lawyer can now review it from the lawyer dashboard.")

    request = st.session_state.get("last_lawyer_request")
    if request:
        brief = (
            "LEXAI CONSULTATION REQUEST\n\n"
            f"Practice area: {request['practice_area']}\n"
            f"Preferred language: {request['language']}\n"
            f"Summary: {request['summary']}\n\n"
            f"Key facts and desired outcome:\n{request['details']}\n\n"
            f"Preferred contact method: {request['contact_method']}\n"
            f"Contact: {request['contact']}\n"
            f"Created: {request['created_at']}\n"
        )
        st.markdown("#### Your consultation brief")
        st.code(brief, language=None)
        st.download_button(
            "Download consultation brief",
            data=brief,
            file_name="lexai_consultation_request.txt",
            mime="text/plain",
        )
        st.markdown(
            "<div class='lexai-disclaimer'>Do not send original identity documents, one-time passwords, or money until you have independently verified the lawyer or legal-aid office.</div>",
            unsafe_allow_html=True,
        )
    persisted_requests = list_citizen_requests(st.session_state["current_user"]["id"])
    if persisted_requests:
        st.subheader("Your saved requests")
        for saved_request in persisted_requests:
            st.markdown(
                f"<div class='lexai-card'><b>{saved_request['summary']}</b><br>"
                f"Status: {saved_request['status']} · Created: {saved_request['created_at']}</div>",
                unsafe_allow_html=True,
            )
            citizen_message = st.text_input("Message your lawyer", key=f"citizen_message_{saved_request['id']}")
            if st.button("Send message", key=f"citizen_send_{saved_request['id']}") and citizen_message.strip():
                send_message(saved_request["id"], st.session_state["current_user"]["id"], citizen_message)
                st.rerun()
            for message_item in list_messages(saved_request["id"]):
                st.caption(f"{message_item['sender_name']} · {message_item['created_at']}: {message_item['body']}")
            citizen_file = st.file_uploader("Share a document", key=f"citizen_document_{saved_request['id']}")
            if citizen_file and st.button("Upload document", key=f"citizen_upload_{saved_request['id']}"):
                add_case_document(
                    saved_request["id"], st.session_state["current_user"]["id"], citizen_file.name,
                    citizen_file.type or "application/octet-stream", citizen_file.getvalue(),
                )
                st.success("Document shared with the case.")
            documents = list_case_documents(saved_request["id"])
            if documents:
                st.caption("Shared documents")
                for document in documents:
                    document_data = get_case_document(document["id"])
                    if document_data:
                        st.download_button(
                            f"Download {document['file_name']}",
                            data=document_data["content"],
                            file_name=document_data["file_name"],
                            mime=document_data["mime_type"],
                            key=f"download_{document['id']}",
                        )
            if saved_request.get("lawyer_id"):
                citizen_appointment = st.text_input("Request consultation time", key=f"citizen_appointment_{saved_request['id']}")
                if citizen_appointment and st.button("Request consultation", key=f"citizen_appointment_button_{saved_request['id']}"):
                    schedule_appointment(
                        saved_request["id"], st.session_state["current_user"]["id"],
                        saved_request["lawyer_id"], citizen_appointment,
                    )
                    st.success("Consultation request recorded.")


# --------------------------------------------------------------------------
# PAGE: Lawyer Dashboard
# --------------------------------------------------------------------------
elif page == "Lawyer Dashboard":
    current_user = st.session_state["current_user"]
    page_header("Lawyer Dashboard", "Manage your professional profile and respond to citizen consultation requests.", "<i class='bi bi-person-badge'></i>")
    profile = get_lawyer_profile(current_user["id"])
    with st.expander("Professional profile", expanded=profile is None):
        with st.form("lawyer_profile_form"):
            bar_number = st.text_input("Bar Council enrolment number", value=profile["bar_council_number"] if profile else "")
            practice_areas = st.text_input("Practice areas", value=profile["practice_areas"] if profile else "")
            lawyer_languages = st.text_input("Languages", value=profile["languages"] if profile else "")
            lawyer_bio = st.text_area("Professional bio", value=profile["bio"] if profile else "")
            save_profile = st.form_submit_button("Save profile", type="primary")
        if save_profile:
            if not bar_number.strip() or not practice_areas.strip() or not lawyer_languages.strip():
                st.error("Bar Council number, practice areas, and languages are required.")
            else:
                create_lawyer_profile(current_user["id"], bar_number, practice_areas, lawyer_languages, lawyer_bio)
                st.success("Profile saved. Verification status remains pending until an authorized reviewer verifies it.")
                st.rerun()
    if profile:
        st.info(f"Verification status: {profile['verification_status']}. Only verified profiles should be presented as verified lawyers.")

    requests = list_lawyer_requests(current_user["id"])
    st.subheader("Consultation requests")
    if not requests:
        st.info("No consultation requests are waiting for you.")
    for request in requests:
        with st.container(border=True):
            st.markdown(
                f"**{request['summary']}**  \n"
                f"From: {request['citizen_name']} ({request['citizen_email']})  \n"
                f"Practice area: {request['practice_area']} · Language: {request['language']}  \n"
                f"Status: **{request['status']}**"
            )
            st.write(request["details"])
            status_col, message_col = st.columns([1, 2])
            with status_col:
                statuses = ["accepted", "declined", "in_progress", "closed"]
                new_status = st.selectbox("Update status", statuses, key=f"status_{request['id']}")
                if st.button("Save status", key=f"save_status_{request['id']}"):
                    update_request_status(request["id"], current_user["id"], new_status)
                    st.rerun()
            with message_col:
                message = st.text_input("Message citizen", key=f"message_{request['id']}")
                if st.button("Send message", key=f"send_message_{request['id']}") and message.strip():
                    send_message(request["id"], current_user["id"], message)
                    st.rerun()
            for item in list_messages(request["id"]):
                st.caption(f"{item['sender_name']} · {item['created_at']}: {item['body']}")
            shared_file = st.file_uploader("Share a case document", key=f"document_{request['id']}")
            if shared_file and st.button("Upload document", key=f"upload_{request['id']}"):
                add_case_document(
                    request["id"], current_user["id"], shared_file.name,
                    shared_file.type or "application/octet-stream", shared_file.getvalue(),
                )
                st.success("Document shared with the case.")
            appointment_time = st.text_input("Requested appointment time", key=f"appointment_{request['id']}")
            if appointment_time and st.button("Request appointment", key=f"appointment_button_{request['id']}"):
                schedule_appointment(request["id"], request["citizen_id"], current_user["id"], appointment_time)
                st.success("Appointment request recorded.")


# --------------------------------------------------------------------------
# PAGE: Legal Education Agent
# --------------------------------------------------------------------------
elif page == "Legal Education":
    page_header("Legal Education", "Understand legal terms and basic procedures in plain language using retrieved sources.", "<i class='bi bi-book'></i>")
    education_language = st.selectbox("Language", LANGUAGES, index=LANGUAGES.index(st.session_state["global_language"]), key="education_lang")
    education_question = st.text_area("What legal concept would you like explained?", placeholder="e.g. What does bail mean?")
    if st.button("Explain concept", type="primary") and education_question.strip():
        with st.status("Retrieving relevant legal sources...", expanded=False):
            education_result = LegalEducationAgent(pipeline).explain(education_question, language=education_language)
        st.markdown(f"<div class='lexai-card'>{education_result['answer']}</div>", unsafe_allow_html=True)
        render_sources(education_result["retrieved_sources"])
        st.markdown(f"<div class='lexai-disclaimer'>{DISCLAIMER}</div>", unsafe_allow_html=True)


# --------------------------------------------------------------------------
# PAGE: Complaint Drafting Agent
# --------------------------------------------------------------------------
elif page == "Complaint Drafting":
    page_header("Complaint Drafting", "Describe what happened and prepare a formal complaint you can review and download.", "<i class='bi bi-file-earmark-plus'></i>")

    language = st.selectbox("Language", LANGUAGES, index=LANGUAGES.index(st.session_state["global_language"]), key="complaint_lang")
    situation = st.text_area(
        "Describe your situation",
        placeholder="e.g. Amazon sent me a damaged laptop and they aren't responding.",
    )

    if st.button("Draft Complaint", type="primary") and situation.strip():
        with st.status("Drafting your complaint...", expanded=False):
            complaint = generate_complaint(situation, language=language)

        if complaint.get("_parse_error"):
            st.warning("Couldn't format this as a structured complaint. Raw output:")
            st.write(complaint.get("_raw"))
        else:
            st.markdown(
                f"""<div class='lexai-card'>
                <span class='lexai-badge'>DRAFT — REVIEW BEFORE SUBMITTING</span>
                <span class='lexai-badge'>{complaint.get('complaint_type','')}</span>
                <h4>{complaint.get('issue_summary','')}</h4>
                <p><b>Complainant:</b> {complaint.get('complainant_placeholder','')}<br>
                <b>Respondent:</b> {complaint.get('respondent_placeholder','')}</p>
                <p><b>Description:</b><br>{complaint.get('description','')}</p>
                <p><b>Relief Requested:</b><br>{complaint.get('relief_requested','')}</p>
                <p><b>Attachments:</b> {', '.join(complaint.get('attachments', []))}</p>
                </div>""",
                unsafe_allow_html=True,
            )

            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                export_complaint_docx(complaint, tmp.name)
                with open(tmp.name, "rb") as f:
                    docx_bytes = f.read()

            st.download_button(
                "Download as Word Document",
                data=docx_bytes,
                file_name=f"{complaint.get('complaint_type','complaint').replace(' ', '_')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
            st.markdown(
                f"<div class='lexai-disclaimer'>{DISCLAIMER} Review carefully before submitting.</div>",
                unsafe_allow_html=True,
            )

            st.session_state.history_complaints.append(complaint)


# --------------------------------------------------------------------------
# PAGE: Document Analysis Agent
# --------------------------------------------------------------------------
elif page == "Document Analysis":
    page_header("Document Analysis", "Upload an FIR, agreement, contract, or notice for a clear plain-language breakdown.", "<i class='bi bi-file-earmark-text'></i>")

    language = st.selectbox("Language", LANGUAGES, index=LANGUAGES.index(st.session_state["global_language"]), key="doc_lang")
    doc_type = st.selectbox(
        "Document type",
        ["general", "fir", "rental_agreement", "employment_contract", "bank_notice", "government_notice"],
    )
    uploaded = st.file_uploader("Upload document (PDF or image)", type=["pdf", "png", "jpg", "jpeg"])

    if uploaded and st.button("Analyze Document", type="primary"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded.name).suffix) as tmp:
            tmp.write(uploaded.read())
            tmp_path = tmp.name

        with st.status("Reading and analyzing the document...", expanded=False):
            result = analyze_document(tmp_path, doc_type=doc_type, language=language)

        st.session_state.last_doc_text = result["extracted_text"]
        st.session_state.last_doc_name = uploaded.name
        st.markdown(f"<div class='lexai-card'>{result['analysis']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='lexai-disclaimer'>{DISCLAIMER}</div>", unsafe_allow_html=True)

        st.session_state.history_documents.append({"name": uploaded.name, "doc_type": doc_type})

    if st.session_state.last_doc_text:
        st.markdown("---")
        st.subheader(f"Ask about: {st.session_state.last_doc_name}")
        followup = st.text_input("e.g. Can my landlord increase the rent?")
        if st.button("Ask") and followup.strip():
            with st.status("Checking the document...", expanded=False):
                answer = ask_about_document(st.session_state.last_doc_text, followup, language=language)
            st.markdown(f"<div class='lexai-card'>{answer}</div>", unsafe_allow_html=True)


# --------------------------------------------------------------------------
# PAGE: Service Navigation Agent
# --------------------------------------------------------------------------
elif page == "Service Navigation":
    page_header("Service Navigation", "Find the right authority, required documents, and next steps for your issue.", "<i class='bi bi-signpost-split'></i>")

    language = st.selectbox("Language", LANGUAGES, index=LANGUAGES.index(st.session_state["global_language"]), key="nav_lang")
    problem = st.text_area("Describe your problem", placeholder="e.g. My employer hasn't paid my salary.")

    if st.button("Get Navigation Plan", type="primary") and problem.strip():
        with st.status("Working out the right path...", expanded=False):
            nav = nav_agent.navigate(problem, language=language)

        if nav.get("_parse_error"):
            st.warning("Couldn't format this as a structured plan. Raw output:")
            st.write(nav.get("_raw"))
        else:
            def flow_step(label, content):
                st.markdown(
                    f"<div class='lexai-flow-step'><b>{label}</b><br>{content}</div>",
                    unsafe_allow_html=True,
                )
                st.markdown("<div class='lexai-flow-arrow'><i class='bi bi-chevron-down'></i></div>", unsafe_allow_html=True)

            flow_step("Problem Identified", nav.get("problem_identified", ""))
            flow_step("Recommended Authority", nav.get("recommended_authority", ""))
            docs_html = "".join(f"✓ {d}<br>" for d in nav.get("documents_required", []))
            flow_step("Documents Required", docs_html or "—")
            steps_html = "".join(f"{i+1}. {s}<br>" for i, s in enumerate(nav.get("procedure_steps", [])))
            flow_step("Procedure", steps_html or "—")

            portal_name = nav.get("official_portal_name") or "—"
            portal_note = nav.get("official_portal_note", "")
            st.markdown(
                f"<div class='lexai-flow-step'><b>Official Portal / Helpline</b><br>{portal_name}<br>"
                f"<span style='color:#666;font-size:0.85rem'>{portal_note}</span></div>",
                unsafe_allow_html=True,
            )
            render_sources([{"source": s, "category": ""} for s in nav.get("_sources", [])])
            st.markdown(f"<div class='lexai-disclaimer'>{DISCLAIMER}</div>", unsafe_allow_html=True)


# --------------------------------------------------------------------------
# PAGE: Document Checklist Agent
# --------------------------------------------------------------------------
elif page == "📋 Document Checklist":
    page_header("Document Checklist", "Find the documents you may need for your legal or government service request.", "<i class='bi bi-clipboard-check'></i>")

    language = st.selectbox("Language", LANGUAGES, index=LANGUAGES.index(st.session_state["global_language"]), key="checklist_lang")
    situation = st.text_area("Describe your situation", placeholder="e.g. I want to file a consumer complaint about a defective product.", key="checklist_situation")

    if st.button("Generate Checklist", type="primary") and situation.strip():
        with st.status("Preparing your document checklist...", expanded=False):
            checklist = generate_checklist(situation, language=language)

        if checklist.get("_parse_error"):
            st.warning("Couldn't format this as a structured checklist. Raw output:")
            st.write(checklist.get("_raw"))
        else:
            st.markdown(
                f"<div class='lexai-card'><b>Situation Summary</b><br>{checklist.get('situation_summary', '')}</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div class='lexai-flow-step'><b>Required Documents</b><br>{''.join(f'✓ {document}<br>' for document in checklist.get('required_documents', [])) or '—'}</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div class='lexai-flow-step'><b>Optional Documents</b><br>{''.join(f'✓ {document}<br>' for document in checklist.get('optional_documents', [])) or '—'}</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div class='lexai-card'><b>Notes</b><br>{checklist.get('notes', '') or '—'}</div>",
                unsafe_allow_html=True,
            )
            render_sources([{"source": source, "category": ""} for source in checklist.get("_sources", [])])


# --------------------------------------------------------------------------
# PAGE: Scam Check
# --------------------------------------------------------------------------
elif page == "Scam Check":
    page_header("Scam Check", "Paste a suspicious SMS, WhatsApp, or email message to assess its risk.", "<i class='bi bi-shield-check'></i>")

    language = st.selectbox("Language", LANGUAGES, index=LANGUAGES.index(st.session_state["global_language"]), key="scam_lang")
    message = st.text_area("Paste the suspicious message here")

    if st.button("Analyze Message", type="primary") and message.strip():
        with st.status("Analyzing message...", expanded=False):
            result = analyze_message(message, language=language)
        st.markdown(f"<div class='lexai-card'>{result['analysis']}</div>", unsafe_allow_html=True)
        if result["rule_based_flags"]:
            st.warning(f"Pattern flags: {', '.join(result['rule_based_flags'])}")


render_footer()
