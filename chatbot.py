from config.prompts import SUPPORTIVE_ASSISTANT_PROMPT, INTRODUCTION_PROMPT
from openai import OpenAI
from supabase import create_client, Client

import streamlit as st
import uuid

# ----------------------------
# App Setup
# ----------------------------

# Initialize Supabase connection
# Uses st.cache_resource to only run once.
@st.cache_resource
def init_connection():
    url = st.secrets['SUPABASE_URL']
    key = st.secrets['SUPABASE_KEY']
    return create_client(url, key)

supabase = init_connection()

@st.cache_data(ttl=500)
def run_query():
    return supabase.table("messages").select("*").execute()

def insert_message(message):
    return supabase.table("messages").insert(message).execute()

def upsert_feedback(feedback):
    return supabase.table("feedback").upsert(feedback, on_conflict="session_id,message_id").execute()

# rows = run_query()
# print(rows.data)

st.title("MilkWise Chatbot")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

SYSTEM_PROMPT = {"role": "system", "content": SUPPORTIVE_ASSISTANT_PROMPT}

# ----------------------------
# Session Initialization
# ----------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    intro_id = str(uuid.uuid4())
    st.session_state.messages = [
        SYSTEM_PROMPT,
        {
            "message_id": intro_id,
            "role": "assistant",
            "content": INTRODUCTION_PROMPT
        }
    ]

# Track last feedback value per message (to detect changes)
if "feedback_state" not in st.session_state:
    st.session_state.feedback_state = {}

# ----------------------------
# Render Chat History + Feedback
# ----------------------------
for message in st.session_state.messages[1:]:
    with st.chat_message(message["role"]):
        st.write(message["content"])

        if message["role"] == "assistant":
            key = f"feedback_{message['message_id']}"
            feedback = st.feedback("thumbs", key=key)

            previous_value = st.session_state.feedback_state.get(message["message_id"])

            # Log immediately if feedback is new or changed
            if feedback is not None and feedback != previous_value:
                st.session_state.feedback_state[message["message_id"]] = feedback

                feedback_message = {
                    "feedback_id": str(uuid.uuid4()),
                    "message_id": message["message_id"],
                    "session_id": st.session_state.session_id,
                    "value": feedback
                }

                upsert_feedback(feedback_message)

# ----------------------------
# User Input
# ----------------------------
prompt = st.chat_input("Ask a question or share a concern")

if prompt:
    user_id = str(uuid.uuid4()) # User message ID

    # Render user message
    with st.chat_message("user"):
        st.markdown(prompt)

    st.session_state.messages.append({
        "message_id": user_id,
        "role": "user",
        "content": prompt
    })

    user_message = {
        "message_id": user_id,
        "session_id": st.session_state.session_id,
        "actor_type": "user",
        "content": prompt
    }
    insert_message(user_message)

    # ----------------------------
    # Assistant Response
    # ----------------------------
    assistant_id = str(uuid.uuid4()) # Assistant message ID

    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=st.session_state.messages,
            stream=True
        )
        response = st.write_stream(stream)

    st.session_state.messages.append({
        "message_id": assistant_id,
        "role": "assistant",
        "content": response
    })

    assistant_message = {
        "message_id": assistant_id,
        "session_id": st.session_state.session_id,
        "actor_type": "assistant",
        "content": response
    }
    insert_message(assistant_message)
