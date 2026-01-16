import json
from datetime import datetime

def log_message(message_id, session_id, actor_type, content):
    log_entry = {
        "message_id": message_id,
        "session_id": session_id,
        "actor_type": actor_type,
        "content": content,
        "timestamp": datetime.now().isoformat()
    }

    with open("chat_logs.json", "a") as f:
        f.write(json.dumps(log_entry) + "\n")