import time
from typing import Dict, Any, List

# In-memory dictionary storing active sessions:
# {
#     session_id: {
#         "user_id": str,
#         "messages": List[Dict[str, str]],
#         "last_activity": float  # timestamp
#     }
# }
active_sessions: Dict[str, Dict[str, Any]] = {}


def init_session(session_id: str, user_id: str) -> Dict[str, Any]:
    """Initialize a new session if it does not exist."""
    if session_id not in active_sessions:
        active_sessions[session_id] = {
            "user_id": user_id,
            "messages": [],
            "last_activity": time.time()
        }
    return active_sessions[session_id]


def update_session(session_id: str, message: Dict[str, str], user_id: str = "default_user") -> None:
    """Update last_activity and append a message to the session."""
    if session_id not in active_sessions:
        init_session(session_id, user_id)
    
    active_sessions[session_id]["messages"].append(message)
    active_sessions[session_id]["last_activity"] = time.time()


def get_stale_sessions(stale_threshold_seconds: float = 1800.0) -> List[str]:
    """Return list of session_ids with last_activity older than threshold (default 30 mins)."""
    current_time = time.time()
    stale_ids = []
    for session_id, session_data in active_sessions.items():
        elapsed = current_time - session_data["last_activity"]
        if elapsed > stale_threshold_seconds:
            stale_ids.append(session_id)
    return stale_ids


def remove_session(session_id: str) -> None:
    """Remove a session from active_sessions."""
    active_sessions.pop(session_id, None)
