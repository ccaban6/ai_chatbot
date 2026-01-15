import json
from datetime import datetime

def log_message(session_id, id, role, content, message_id):
    log_entry = {
        "session_id": session_id,
        "id": id,
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(),
        "message_id": message_id
    }

    with open("chat_logs.json", "a") as f:
        f.write(json.dumps(log_entry) + "\n")