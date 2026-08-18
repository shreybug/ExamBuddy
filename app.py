import streamlit as st
import os
import tempfile
import time
import json
import sqlite3
import base64
from dotenv import load_dotenv
from google import genai
from google.genai import types

# 1. Load environment variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# 2. Page Configuration
st.set_page_config(
    page_title="ExamBuddy",
    page_icon="logo.png" if os.path.exists("logo.png") else None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Helper function to encode local image for CSS background
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return None

SUPPORTED_FILE_TYPES = ["pdf", "png", "jpg", "jpeg"]

# Locate the workspace background image
bg_base64 = get_base64_image("background.png") or get_base64_image("background.jpg")

# 3. Custom CSS
st.markdown("""
<style>
    /* Global Matte Black Background */
    .stApp {
        background-color: #28282B !important;
        color: #FFFFFF !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        font-size: 1.15rem !important;
    }
    
    [data-testid="stSidebar"] {
        background-color: rgba(32, 32, 35, 0.95) !important;
        backdrop-filter: blur(10px);
        border-right: 2px solid #38383D !important;
    }

    /* Workspace-specific background with background.png */
    .workspace-active {
        background-color: transparent !important;
    }

    /* Extra-Large Selected Subject Header */
    .subject-title {
        color: #FFFFFF !important;
        font-size: 3.2rem !important;
        font-weight: 850 !important;
        letter-spacing: -1px;
        margin-bottom: 0px !important;
        line-height: 1.1 !important;
        border-left: 6px solid #FF5722;
        padding-left: 14px;
    }

    /* General Typography */
    h1 {
        color: #FFFFFF !important;
        font-size: 2.5rem !important;
        font-weight: 800 !important;
    }
    h2 {
        color: #FFFFFF !important;
        font-size: 2.1rem !important;
        font-weight: 750 !important;
    }
    h3 {
        color: #FFE0B2 !important;
        font-size: 1.65rem !important;
        font-weight: 700 !important;
    }
    h4 {
        color: #FF8A65 !important;
        font-size: 1.35rem !important;
        font-weight: 650 !important;
    }
    p, span, label, li {
        font-size: 1.12rem !important;
        line-height: 1.6 !important;
    }
    .stCaption, [data-testid="stCaptionContainer"] p {
        font-size: 0.98rem !important;
        color: #FFE0B2 !important;
    }

    /* Glassmorphic Login Card */
    .login-card {
        background: rgba(40, 40, 43, 0.95);
        border: 2px solid #FF7043;
        border-radius: 16px;
        padding: 30px;
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.8), 0 0 20px rgba(255, 112, 67, 0.2);
        width: 100%;
        max-width: 420px;
    }

    /* Interactive Workspace Cards */
    .interactive-card {
        background-color: rgba(50, 50, 54, 0.85);
        backdrop-filter: blur(8px);
        border: 2px solid #3F3F46;
        border-radius: 14px;
        padding: 20px 24px;
        margin-bottom: 18px;
        transition: all 0.25s ease;
    }
    .interactive-card:hover {
        border-color: #FF7043;
        box-shadow: 0 4px 20px rgba(255, 112, 67, 0.25);
    }
    
    /* Status Badges */
    .status-badge-active {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 20px;
        background-color: rgba(255, 87, 34, 0.25);
        color: #FF8A65;
        border: 1.5px solid #FF7043;
        font-size: 0.95rem !important;
        font-weight: 700;
    }
    
    .status-badge-inactive {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 20px;
        background-color: rgba(255, 255, 255, 0.08);
        color: #BDBDBD;
        border: 1.5px solid #4E4E54;
        font-size: 0.95rem !important;
        font-weight: 600;
    }

    /* Streamlit Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background-color: rgba(32, 32, 35, 0.85);
        backdrop-filter: blur(6px);
        padding: 10px;
        border-radius: 12px;
        border: 1.5px solid #3E3E44;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: #FFE0B2 !important;
        padding: 10px 20px;
        font-size: 1.1rem !important;
        font-weight: 700;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FF5722 !important;
        color: #FFFFFF !important;
        box-shadow: 0 0 15px rgba(255, 87, 34, 0.4);
    }

    /* Buttons with Orange Highlights */
    .stButton>button {
        background: rgba(52, 52, 56, 0.9) !important;
        color: #FFFFFF !important;
        border: 1.5px solid #FF7043 !important;
        border-radius: 10px !important;
        padding: 0.6rem 1.2rem !important;
        font-size: 1.08rem !important;
        font-weight: 650 !important;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        background: #FF5722 !important;
        border-color: #FF8A65 !important;
        color: #FFFFFF !important;
        box-shadow: 0 0 18px rgba(255, 87, 34, 0.5);
    }
    
    /* Text Inputs & Selectboxes */
    .stTextInput>div>div>input, .stSelectbox>div>div {
        background-color: rgba(31, 31, 34, 0.9) !important;
        border: 1.5px solid #FF8A65 !important;
        color: #FFFFFF !important;
        border-radius: 10px !important;
        font-size: 1.1rem !important;
        padding: 10px !important;
    }
    .stTextInput>div>div>input:focus {
        border-color: #FF5722 !important;
        box-shadow: 0 0 10px rgba(255, 87, 34, 0.4) !important;
    }

    /* Chat Messages */
    [data-testid="stChatMessage"] {
        background-color: rgba(49, 49, 54, 0.88) !important;
        backdrop-filter: blur(8px);
        border: 1.5px solid #43434A !important;
        border-radius: 14px !important;
        padding: 16px !important;
        margin-bottom: 16px !important;
        font-size: 1.15rem !important;
    }

    /* Chat Input Terminal */
    [data-testid="stChatInput"] {
        background-color: rgba(30, 30, 33, 0.95) !important;
        backdrop-filter: blur(10px);
        border: 2px solid #FF7043 !important;
        border-radius: 12px !important;
        box-shadow: 0 0 15px rgba(255, 112, 67, 0.25) !important;
    }
    [data-testid="stChatInput"] textarea {
        font-size: 1.15rem !important;
        color: #FFFFFF !important;
    }
</style>
""", unsafe_allow_html=True)

# 4. Local Database Persistence
DB_FILE = "exambuddy_data.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_data (
            username TEXT,
            subject TEXT,
            chat_history TEXT,
            PRIMARY KEY (username, subject)
        )
    """)
    conn.commit()
    conn.close()

def save_chat_to_db(username, subject, chat_history):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO user_data (username, subject, chat_history)
        VALUES (?, ?, ?)
    """, (username, subject, json.dumps(chat_history)))
    conn.commit()
    conn.close()

def load_chat_from_db(username, subject):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT chat_history FROM user_data WHERE username = ? AND subject = ?", (username, subject))
    row = c.fetchone()
    conn.close()
    if row and row[0]:
        return json.loads(row[0])
    return []

def get_saved_subjects(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT DISTINCT subject FROM user_data WHERE username = ?", (username,))
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows] if rows else ["General Engineering"]

init_db()

# 5. User Authentication State & Login Screen
if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None

def login_screen():
    col_art, col_space, col_login = st.columns([1.6, 0.2, 1.2])

    with col_art:
        if os.path.exists("logo.png"):
            st.image("logo.png", use_container_width=True)

    with col_login:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div class="login-card">
            <h3 style="margin-top: 0; color: #FF8A65;">Enter Workspace</h3>
            <p style="color: #FFE0B2; font-size: 1rem; margin-bottom: 20px;">Access your saved subjects, papers & predicted questions.</p>
        """, unsafe_allow_html=True)
        
        email_or_name = st.text_input("Name or Email ID", placeholder="student@college.edu")
        if st.button("Access ExamBuddy", use_container_width=True):
            if email_or_name.strip():
                st.session_state.authenticated_user = email_or_name.strip()
                if "subjects" in st.session_state:
                    del st.session_state["subjects"]
                if "current_subject" in st.session_state:
                    del st.session_state["current_subject"]
                st.rerun()
            else:
                st.error("Please enter a valid name or email.")
        
        st.markdown("<div style='text-align:center; color:#FF8A65; margin: 12px 0; font-size: 0.95rem;'>or</div>", unsafe_allow_html=True)
        
        if st.button("Sign in with Google", use_container_width=True):
            st.session_state.authenticated_user = "student@google.com"
            if "subjects" in st.session_state:
                del st.session_state["subjects"]
            if "current_subject" in st.session_state:
                del st.session_state["current_subject"]
            st.rerun()
            
        st.markdown("</div>", unsafe_allow_html=True)

if not st.session_state.authenticated_user:
    login_screen()
    st.stop()

# 6. Apply background.png ONLY in the Logged-in Workspace
if bg_base64:
    st.markdown(f"""
    <style>
        .stApp {{
            background: linear-gradient(rgba(40, 40, 43, 0.88), rgba(40, 40, 43, 0.92)),
                        url("data:image/png;base64,{bg_base64}") no-repeat center center fixed !important;
            background-size: cover !important;
        }}
    </style>
    """, unsafe_allow_html=True)

# 7. Gemini Client & Fallback Configuration
client = genai.Client(api_key=api_key)

MODELS_TO_TRY = [
    "gemini-flash-latest",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.6-flash"
]

def generate_content_with_fallback(contents, system_instruction=None):
    last_error = None
    config = types.GenerateContentConfig(
        system_instruction=system_instruction
    ) if system_instruction else None

    for model_name in MODELS_TO_TRY:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )
            return response.text
        except Exception as e:
            last_error = e
            time.sleep(1)
            continue
    raise last_error

def upload_file_to_gemini(uploaded_file):
    file_ext = os.path.splitext(uploaded_file.name)[1].lower()
    if not file_ext:
        file_ext = ".pdf"
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    
    gemini_file_ref = client.files.upload(file=tmp_path)
    os.remove(tmp_path)
    return gemini_file_ref

# 8. Session Data Setup
username = st.session_state.authenticated_user

if "subjects" not in st.session_state or not st.session_state.subjects:
    saved = get_saved_subjects(username)
    st.session_state.subjects = {
        s: {
            "chat_history": load_chat_from_db(username, s),
            "syllabus_refs": [],
            "paper_refs": []
        } for s in saved
    }

if "current_subject" not in st.session_state or st.session_state.current_subject not in st.session_state.subjects:
    st.session_state.current_subject = list(st.session_state.subjects.keys())[0]

current_subj = st.session_state.current_subject

if current_subj not in st.session_state.subjects:
    st.session_state.subjects[current_subj] = {
        "chat_history": [],
        "syllabus_refs": [],
        "paper_refs": []
    }

current_data = st.session_state.subjects[current_subj]

SYSTEM_INSTRUCTION = """
You are ExamBuddy, an expert academic advisor and examination trend analyst.
You have access to uploaded materials which may be PDFs or direct images/photos (PNG, JPG) of documents:
1. OFFICIAL SYLLABUS: Contains course units, modules, and learning outcomes.
2. PREVIOUS YEAR QUESTION PAPERS (PYQs): Historical exams containing questions, marks, and distribution patterns.

Core rules:
- Read both typed text and scanned/handwritten paper photos accurately.
- Map questions directly to Syllabus Modules/Units.
- Distinguish clearly between syllabus requirements and historical trends.
- Solve both exam questions and generated practice problems with complete step-by-step logic.
"""

# 9. Sidebar Controls
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=140)
    st.caption(f"Account: `{username}`")
    if st.button("Sign Out", use_container_width=True):
        st.session_state.authenticated_user = None
        st.session_state.subjects = {}
        st.rerun()

    st.divider()
    st.markdown("#### Select Subject")
    
    subject_list = list(st.session_state.subjects.keys())
    selected_subject = st.selectbox(
        "Current Subject",
        options=subject_list,
        index=subject_list.index(current_subj),
        label_visibility="collapsed"
    )
    if selected_subject != st.session_state.current_subject:
        st.session_state.current_subject = selected_subject
        st.rerun()

    with st.expander("+ Create New Subject"):
        new_name = st.text_input("Subject Title", placeholder="e.g., Data Structures")
        if st.button("Add Subject", use_container_width=True):
            clean = new_name.strip()
            if clean and clean not in st.session_state.subjects:
                st.session_state.subjects[clean] = {
                    "chat_history": [],
                    "syllabus_refs": [],
                    "paper_refs": []
                }
                st.session_state.current_subject = clean
                st.rerun()

    st.divider()
    st.markdown("#### Document Hub")
    
    uploaded_syllabus = st.file_uploader(
        "Official Syllabus (PDF, PNG, JPG)",
        type=SUPPORTED_FILE_TYPES,
        key=f"syllabus_{current_subj}"
    )

    uploaded_papers = st.file_uploader(
        "Previous Question Papers (PDFs / Images)",
        type=SUPPORTED_FILE_TYPES,
        accept_multiple_files=True,
        key=f"papers_{current_subj}"
    )

    if (uploaded_syllabus or uploaded_papers) and (not current_data["syllabus_refs"] and not current_data["paper_refs"]):
        if st.button("⚡ Process & Index Documents", use_container_width=True):
            with st.spinner("Processing documents & images..."):
                try:
                    if uploaded_syllabus:
                        current_data["syllabus_refs"] = [upload_file_to_gemini(uploaded_syllabus)]

                    if uploaded_papers:
                        p_refs = []
                        for p in uploaded_papers:
                            p_refs.append(upload_file_to_gemini(p))
                        current_data["paper_refs"] = p_refs

                    st.success("Documents & images synchronized!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# 10. Main Workspace Header & Controls
header_left, header_right = st.columns([2.5, 1])

with header_left:
    st.markdown(f'<div class="subject-title">{current_subj}</div>', unsafe_allow_html=True)
    st.caption(f"Active workspace session for **{username}**")

with header_right:
    s_badge = '<span class="status-badge-active">Syllabus Active</span>' if current_data["syllabus_refs"] else '<span class="status-badge-inactive">No Syllabus</span>'
    p_badge = f'<span class="status-badge-active">{len(current_data["paper_refs"])} Files Loaded</span>' if current_data["paper_refs"] else '<span class="status-badge-inactive">0 Files Loaded</span>'
    st.markdown(f"<div style='text-align:right; margin-top:15px;'>{s_badge} &nbsp; {p_badge}</div>", unsafe_allow_html=True)

# 11. Interactive Tabs Workspace
tab_chat, tab_presets, tab_checklist, tab_export = st.tabs([
    "💬 Chat & Solutions",
    "⚡ One-Click Generator",
    "✅ Revision Checklist",
    "📥 Export Study Guide"
])

def run_gemini_query(prompt_text):
    if not current_data["paper_refs"] and not current_data["syllabus_refs"]:
        st.warning("Please upload syllabus or question paper files (PDF/Images) in the sidebar first.")
        return

    all_docs = current_data["syllabus_refs"] + current_data["paper_refs"]
    conversation_contents = []
    
    for i, turn in enumerate(current_data["chat_history"]):
        if i == 0 and turn["role"] == "user":
            parts = all_docs + [turn["text"]]
        else:
            parts = [turn["text"]]
        
        conversation_contents.append(
            types.Content(role=turn["role"], parts=[types.Part.from_text(text=p) if isinstance(p, str) else p for p in parts])
        )

    if not conversation_contents:
        first_turn_parts = all_docs + [prompt_text]
        conversation_contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=p) if isinstance(p, str) else p for p in first_turn_parts]
            )
        )
    else:
        conversation_contents.append(
            types.Content(role="user", parts=[types.Part.from_text(text=prompt_text)])
        )

    current_data["chat_history"].append({"role": "user", "text": prompt_text})

    with st.spinner("ExamBuddy is analyzing..."):
        try:
            response_text = generate_content_with_fallback(
                contents=conversation_contents,
                system_instruction=SYSTEM_INSTRUCTION
            )
            current_data["chat_history"].append({"role": "model", "text": response_text})
            save_chat_to_db(username, current_subj, current_data["chat_history"])
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

# TAB 1: Chat & Solutions
with tab_chat:
    st.markdown("##### Quick Action Presets")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📊 Full Trend Report", use_container_width=True):
            run_gemini_query("Generate a full Module-wise Weightage table, repeated theorems, and exam priorities.")
    with c2:
        if st.button("🔍 Syllabus Audit", use_container_width=True):
            run_gemini_query("Compare syllabus units against the question papers and list overlooked vs heavily tested units.")

    st.markdown("<br>", unsafe_allow_html=True)
    
    avatar_path = "logo.png" if os.path.exists("logo.png") else None
    for message in current_data["chat_history"]:
        role_label = "assistant" if message["role"] == "model" else "user"
        avatar_to_show = avatar_path if role_label == "assistant" else None
        with st.chat_message(role_label, avatar=avatar_to_show):
            st.markdown(message["text"])

    user_query = st.chat_input("Ask ExamBuddy a question, request solutions, or practice problems...")
    if user_query:
        run_gemini_query(user_query)

# TAB 2: One-Click Generator
with tab_presets:
    st.markdown("### Interactive Practice & Generator Hub")
    st.caption("Generate targeted study material grounded in your uploaded papers and images.")
    
    gen_col1, gen_col2 = st.columns(2)
    with gen_col1:
        st.markdown("""
        <div class="interactive-card">
            <h4>💡 High-Yield Formula & Derivations Sheet</h4>
            <p style="color: #FFE0B2; font-size: 1rem;">Extracts all recurring formulas, proofs, and definitions from past exams.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Generate Formula & Derivations Sheet", use_container_width=True):
            run_gemini_query("Extract and summarize all important recurring definitions, formulas, and derivations into a structured cheat sheet.")

    with gen_col2:
        st.markdown("""
        <div class="interactive-card">
            <h4>⚡ 3-Mark Quick Review Questions</h4>
            <p style="color: #FFE0B2; font-size: 1rem;">Generates short concept-testing questions with step-by-step answers.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Generate Short Concept Questions", use_container_width=True):
            run_gemini_query("Generate 5 short 2-mark/3-mark questions from high-weightage topics with concise answers.")

# TAB 3: Revision Checklist
with tab_checklist:
    st.markdown("### Interactive Study Tracker")
    st.caption("Mark off high-yield topics as you complete your revisions.")
    
    st.checkbox("Review Module 1 core definitions and theorems", key=f"chk1_{current_subj}")
    st.checkbox("Practice high-frequency derivations identified in PYQs", key=f"chk2_{current_subj}")
    st.checkbox("Solve high-probability long-form questions", key=f"chk3_{current_subj}")
    st.checkbox("Self-test on out-of-syllabus or low-yield edge questions", key=f"chk4_{current_subj}")

# TAB 4: Export Study Guide
with tab_export:
    st.markdown("### Download Study Notes")
    st.caption("Export your AI-generated weightage analysis and solutions as a Markdown file.")
    
    chat_text_export = f"# ExamBuddy Revision Guide: {current_subj}\n\n"
    for msg in current_data["chat_history"]:
        prefix = "### Student Query" if msg["role"] == "user" else "### ExamBuddy Analysis"
        chat_text_export += f"{prefix}\n\n{msg['text']}\n\n---\n\n"

    st.download_button(
        label="📥 Download Study Guide (.md)",
        data=chat_text_export,
        file_name=f"{current_subj}_Study_Guide.md",
        mime="text/markdown",
        use_container_width=True
    )