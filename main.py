import streamlit as st
import pymupdf
import google.generativeai as genai
import os
from dotenv import load_dotenv
import re
import PyPDF2
import pandas as pd
from datetime import datetime
import pyttsx3
import tempfile

# Load API credentials from .env
load_dotenv()
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini
genai.configure(api_key=GEMINI_KEY)
llm = genai.GenerativeModel("gemini-2.0-flash-lite")

# Utilities
def normalize_text(raw_text):
    cleaned = re.sub(r'\s+', ' ', raw_text.strip().lower())
    return cleaned

def fetch_pdf_text(uploaded_file):
    combined = ""
    document = pymupdf.open(stream=uploaded_file.read(), filetype="pdf")
    for pg in document:
        combined += pg.get_text("text")
    return normalize_text(combined)

def query_response(body, question, style="Formal"):
    tones = {
        "Formal": "Please respond in a professional and formal tone.",
        "Friendly": "Please respond in a warm and friendly tone, as if chatting casually."
    }

    instruction = tones.get(style, "")
    prompt_text = f"""
Content:
{body}

Question:
{question}

{instruction}

Provide a short, clear response.
"""

    try:
        result = llm.generate_content(prompt_text)
        return result.candidates[0].content.parts[0].text if result.candidates else "No reply available."
    except Exception as err:
        return f"⚠️ Error occurred: {str(err)}"

HISTORY_FILE = "chat_log.xlsx"

def append_to_log(q, a, tone_used):
    record = {
        "Time": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "Prompt": [q],
        "Response": [a],
        "Style": [tone_used]
    }

    new_df = pd.DataFrame(record)
    try:
        if os.path.isfile(HISTORY_FILE):
            existing = pd.read_excel(HISTORY_FILE)
            combined_df = pd.concat([existing, new_df], ignore_index=True)
        else:
            combined_df = new_df

        combined_df.to_excel(HISTORY_FILE, index=False, engine="openpyxl")
    except Exception as err:
        st.error(f"❌ Unable to log conversation: {err}")

# Prepare session content from static PDF
with open('science.pdf', 'rb') as pdf:
    pdf_reader = PyPDF2.PdfReader(pdf)
    raw_text = ''.join([page.extract_text() for page in pdf_reader.pages])
    st.session_state['doc_text'] = normalize_text(raw_text)

# UI Setup
st.set_page_config(page_title="Ask Pakistan PDF", page_icon="📄")
st.title("📄 Science for kids - PDF Bot")
st.markdown("---")

tone_choice = st.radio("🗣️ Select Response Style:", ("Professional 🎓", "Conversational 🗨️"), index=0)
tone_map = {"Professional 🎓": "Formal", "Conversational 🗨️": "Friendly"}
active_tone = tone_map[tone_choice]

user_input = st.text_input("❔ Enter your question below:")

if st.button("Get Response") and st.session_state.get('doc_text'):
    pdf_content = st.session_state['doc_text']
    reply = query_response(pdf_content, user_input, active_tone)
    plain_reply = reply.replace('*', '')

    st.subheader("📋 Response:")
    st.text(plain_reply)
    st.markdown(reply)

    # Voice Output
    tts = pyttsx3.init()
    audio_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save_to_file(reply, audio_file.name)
    tts.runAndWait()
    audio_file.close()
    st.audio(audio_file.name)

    append_to_log(user_input, reply, active_tone)

# Display chat history
st.markdown("---")
st.subheader("📑 Previous Interactions")
if os.path.exists(HISTORY_FILE):
    log_df = pd.read_excel(HISTORY_FILE)
    st.dataframe(log_df)
else:
    st.info("ℹ️ No previous records available.")

