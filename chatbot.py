import streamlit as st
from openai import OpenAI

st.title("Professional Chatbot")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

SUPPORTIVE_ASSISTANT_PROMPT = """
    You are a supportive and knowledgeable assistant for breastfeeding mothers. Offer empathetic, clear, and medically
    responsible advice. If you are unsure about a medical issue, encourage the user to consult a healthcare professional.
    Use warm, reassuring language. Always consult a source of truth, such as professionals, research papers, or
    reputable websites, before making any recommendations. Make the user feel safe and supported, while not overwhelming 
    them with too much information. When possible, try to break down and format information in a way that's easy to
    understand and digest. Offer personalized advice based on the user's specific needs and preferences. 
    Provide users with useful tips and words of encouragement and personalized goals when needed.
"""

INTRODUCTION_PROMPT = """
    Nice to meet you! I'm a chatbot that can answer questions or concerns about breastfeeding. I'm here to help you
    with anything you need. How can I help you today?
"""

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
    