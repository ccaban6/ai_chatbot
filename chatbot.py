import streamlit as st
from openai import OpenAI
from config.prompts import SUPPORTIVE_ASSISTANT_PROMPT, INTRODUCTION_PROMPT

st.title("Personal Chatbot")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


# message = role + content
# {role: user, content: hi}
# {role: assistant, content: Hi! I am a chatbot...}

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
            {"role": "system", "content": SUPPORTIVE_ASSISTANT_PROMPT},
            {"role": "assistant", "content": INTRODUCTION_PROMPT}
        ]

# Display chat messages
for message in st.session_state.messages[1:]:
    with st.chat_message(message["role"]):
        st.write(message["content"])

prompt = st.chat_input("Ask a question or share a concern")
if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=st.session_state.messages,
            stream=True
        )
        response = st.write_stream(stream)
    st.session_state.messages.append({"role": "assistant", "content": response})
    