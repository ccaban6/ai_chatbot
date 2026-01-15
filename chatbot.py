import streamlit as st
from openai import OpenAI
from config.prompts import SUPPORTIVE_ASSISTANT_PROMPT, INTRODUCTION_PROMPT
import uuid
import logger

# ----------------------------
# App Setup
# ----------------------------
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
            "id": intro_id,
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
            key = f"feedback_{message['id']}"
            feedback = st.feedback("thumbs", key=key)

            previous_value = st.session_state.feedback_state.get(message["id"])

            # Log immediately if feedback is new or changed
            if feedback is not None and feedback != previous_value:
                st.session_state.feedback_state[message["id"]] = feedback

                logger.log_message(
                    st.session_state.session_id,
                    message["id"],          # actor_id = assistant message id
                    "feedback",
                    feedback,
                    message["id"]           # feedback is tied to this message
                )

# ----------------------------
# User Input
# ----------------------------
prompt = st.chat_input("Ask a question or share a concern")

if prompt:
    user_id = str(uuid.uuid4())

    # Render user message
    with st.chat_message("user"):
        st.markdown(prompt)

    st.session_state.messages.append({
        "id": user_id,
        "role": "user",
        "content": prompt
    })

    logger.log_message(
        st.session_state.session_id,
        user_id,
        "user",
        prompt,
        user_id
    )

    # ----------------------------
    # Assistant Response
    # ----------------------------
    assistant_id = str(uuid.uuid4())

    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=st.session_state.messages,
            stream=True
        )
        response = st.write_stream(stream)

    st.session_state.messages.append({
        "id": assistant_id,
        "role": "assistant",
        "content": response
    })

    logger.log_message(
        st.session_state.session_id,
        assistant_id,
        "assistant",
        response,
        assistant_id
    )
