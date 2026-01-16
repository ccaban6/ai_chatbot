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
# Starter Prompts
# ----------------------------
SUGGESTIONS = {
    ":blue[:material/help: How do I know if my baby is getting enough milk?]": 
        "How do I know if my baby is getting enough milk? What signs should I look for?",
    ":green[:material/schedule: Creating a pumping schedule]": 
        "Help me create a pumping and breastfeeding schedule. I'm worried about maintaining my supply when I return to work.",
    ":orange[:material/medical_services: Dealing with sore nipples]": 
        "My nipples are very sore and cracked. What can I do to help with the pain and healing?",
    ":violet[:material/info: Increasing milk supply]": 
        "I'm concerned about my milk supply. What are some safe and effective ways to increase it?",
    ":red[:material/family_restroom: Breastfeeding positions and latching]": 
        "What are the best breastfeeding positions for a good latch? I'm having trouble getting my baby to latch correctly.",
}

# ----------------------------
# Escalation Detection
# ----------------------------
EMERGENCY_KEYWORDS = [
    "can't breathe", "can't breath", "choking", "not breathing", "stopped breathing",
    "unconscious", "passed out", "fainted", "seizure", "convulsion",
    "severe bleeding", "heavy bleeding", "bleeding heavily",
    "severe allergic reaction", "anaphylaxis", "throat closing",
    "severe pain", "excruciating pain", "unbearable pain",
    "high fever", "very high fever", "fever over 104", "fever 104",
    "blue", "turning blue", "lips blue", "skin blue",
    "emergency", "urgent", "immediately", "right now", "asap",
    "call 911", "911", "ambulance", "er", "emergency room"
]

PROFESSIONAL_CONSULT_KEYWORDS = [
    "persistent", "chronic", "ongoing", "continuing", "lasting",
    "severe", "extreme", "intense", "worsening", "getting worse",
    "infection", "infected", "mastitis", "abscess", "fever",
    "blood", "bleeding", "discharge", "pus", "foul smell",
    "lump", "mass", "hard area", "red streak", "redness spreading",
    "medication", "prescription", "antibiotics", "drug",
    "diagnosis", "diagnosed", "condition", "disease", "illness",
    "doctor", "physician", "pediatrician", "lactation consultant",
    "hospital", "clinic", "medical", "healthcare provider"
]

def detect_escalation(prompt):
    """
    Analyzes user prompt for emergency or professional consultation needs.
    Returns a tuple: (is_emergency, needs_professional_consult)
    """
    prompt_lower = prompt.lower()
    
    # Check for emergency keywords
    is_emergency = any(keyword in prompt_lower for keyword in EMERGENCY_KEYWORDS)
    
    # Check for professional consultation keywords
    needs_professional = any(keyword in prompt_lower for keyword in PROFESSIONAL_CONSULT_KEYWORDS)
    
    return is_emergency, needs_professional

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
# Disclaimer Dialog
# ----------------------------
@st.dialog("Disclaimer")
def show_disclaimer_dialog():
    st.markdown("""
        This AI model may provide inaccurate information and should not be used as 
        the sole source of truth. Always consult with qualified healthcare professionals 
        for medical advice and decisions.
    """)

# Check if there are any user messages yet
has_user_messages = any(
    msg.get("role") == "user" for msg in st.session_state.messages[1:]
)

# Show disclaimer button only before first user input
# if not has_user_messages:
st.button(
    "&nbsp;:small[:gray[:material/info: Disclaimer]]",
    type="tertiary",
    on_click=show_disclaimer_dialog,
)

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
# Show different UI before first user interaction
prompt = st.chat_input("Ask a question or share a concern")
if not has_user_messages:
    
    # Check if user just clicked a suggestion
    user_just_clicked_suggestion = (
        "selected_suggestion" in st.session_state and st.session_state.selected_suggestion
    )
    # Only show pills if we're not about to process a prompt
    
    # Use suggestion as prompt if selected and no direct input
    if not prompt and user_just_clicked_suggestion:
        prompt = SUGGESTIONS[st.session_state.selected_suggestion]

    if not prompt:
        selected_suggestion = st.pills(
            label="Examples",
            label_visibility="collapsed",
            options=SUGGESTIONS.keys(),
            key="selected_suggestion",
        )
        
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


    # ----------------------------
    # Escalation Detection & Guidance
    # ----------------------------
    is_emergency, needs_professional = detect_escalation(prompt)
    
    if is_emergency:
        st.error("""
        ⚠️ **EMERGENCY SITUATION DETECTED**
        
        This appears to be a medical emergency. Please:
        - **Call 911 or go to your nearest emergency room immediately**
        - Do not wait for a response from this chatbot
        - Seek immediate medical attention
        
        This chatbot is not a substitute for emergency medical care.
        """)
    
    elif needs_professional:
        st.warning("""
        💡 **PROFESSIONAL CONSULTATION RECOMMENDED**
        
        Based on your message, we recommend consulting with a healthcare professional:
        - Contact your doctor, pediatrician, or lactation consultant
        - Seek professional medical advice for proper diagnosis and treatment
        - This chatbot provides general information but cannot replace professional medical care
        """)

    user_message = {
        "message_id": user_id,
        "session_id": st.session_state.session_id,
        "actor_type": "user",
        "content": prompt,
        "is_emergency": int(is_emergency),
        "needs_professional": int(needs_professional)
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
        "content": response,
        "is_emergency": int(is_emergency),
        "needs_professional": int(needs_professional)
    }
    insert_message(assistant_message)
