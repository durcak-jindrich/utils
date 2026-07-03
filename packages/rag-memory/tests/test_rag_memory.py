import os
import time
import pytest
from fastapi.testclient import TestClient

# Force mock embeddings and Pinecone during tests to prevent external API calls
os.environ["MOCK_EMBEDDINGS"] = "true"
# Also set placeholder keys if they are not already set, so mock mode triggers automatically
if not os.environ.get("PINECONE_API_KEY"):
    os.environ["PINECONE_API_KEY"] = "placeholder-key"
if not os.environ.get("GROQ_API_KEY"):
    os.environ["GROQ_API_KEY"] = "placeholder-key"

from rag_memory.main import app
from rag_memory.session_store import active_sessions, get_stale_sessions, remove_session
from rag_memory.config import get_pinecone_index
from rag_memory.memory import get_relevant_memory, save_session_summary


@pytest.fixture(autouse=True)
def clean_stores():
    """Clear memory database and active session stores before each test."""
    active_sessions.clear()
    index = get_pinecone_index()
    # If it is MockPineconeIndex, reset its inner DB
    if hasattr(index, "db"):
        index.db.clear()
    yield


def test_full_flow():
    client = TestClient(app)
    
    # 1. Run /ingest and verify success
    response = client.post("/ingest")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Successfully ingested" in data["message"]
    
    # Verify that mock Pinecone index has data in namespace "documents"
    index = get_pinecone_index()
    assert hasattr(index, "db")
    assert "documents" in index.db
    assert len(index.db["documents"]) > 0
    logger_keys = list(index.db["documents"].keys())
    # Should have ingested 20 items (10 customers + 10 meeting notes)
    assert len(logger_keys) == 20
    
    # 2. Send 6 /chat messages as user_id=rep_001
    user_id = "rep_001"
    session_id = "session_test_1"
    
    # We will send 6 messages
    for i in range(1, 7):
        payload = {
            "user_id": user_id,
            "session_id": session_id,
            "message": f"Message number {i} regarding Acme Corp"
        }
        res = client.post("/chat", json=payload)
        assert res.status_code == 200
        chat_data = res.json()
        assert "answer" in chat_data
        
        # Verify incremental summary is saved to Pinecone after message 5
        if i < 5:
            # Memory namespace should be empty or not contain this session yet
            if "memory" in index.db:
                assert session_id not in index.db["memory"]
        elif i == 5:
            # Right after the 5th message, the summary should be saved to Pinecone namespace memory
            assert "memory" in index.db
            assert session_id in index.db["memory"]
            summary_vec = index.db["memory"][session_id]
            assert summary_vec["metadata"]["user_id"] == user_id
            assert "Acme Corp" in summary_vec["metadata"]["text"]
            assert "Message number 5" in summary_vec["metadata"]["text"]
            print(f"Verified summary exists after message 5: {summary_vec['metadata']['text']}")
        elif i == 6:
            # After message 6, the summary should still exist
            assert session_id in index.db["memory"]

    # 3. Mock stale session (>30 mins) and verify background task behavior
    # We will manually trigger the same logic as the background task stale session check
    assert session_id in active_sessions
    # Backdate the activity time to 31 minutes ago (31 * 60 = 1860 seconds)
    active_sessions[session_id]["last_activity"] = time.time() - 1860.0
    
    # Verify it is returned by get_stale_sessions
    stale_sessions = get_stale_sessions(stale_threshold_seconds=1800.0)
    assert session_id in stale_sessions
    
    # Run the cleanup logic: save summary and remove
    for stale_id in stale_sessions:
        s_data = active_sessions[stale_id]
        s_user_id = s_data["user_id"]
        s_history = s_data["messages"]
        
        # Saves summary
        save_session_summary(s_user_id, stale_id, s_history)
        # Removes from active
        remove_session(stale_id)
        
    # Verify session is removed from active sessions
    assert session_id not in active_sessions
    # But the summary remains in the memory namespace of Pinecone
    assert session_id in index.db["memory"]
    
    # 4. Start a new session with the same user_id and verify vague query returns context from the previous session
    new_session_id = "session_test_2"
    payload = {
        "user_id": user_id,
        "session_id": new_session_id,
        "message": "anything new with my accounts?"
    }
    
    # Before we call the API, let's manually verify get_relevant_memory works for the new session
    rel_mem = get_relevant_memory(user_id, "anything new with my accounts?")
    assert "Acme Corp" in rel_mem
    assert "Message number 6" in rel_mem
    
    # Call the API
    res = client.post("/chat", json=payload)
    assert res.status_code == 200
    chat_data = res.json()
    answer = chat_data["answer"]
    
    # Verify mock response includes the retrieved memory content
    assert "Message number 6" in answer
    assert "Acme Corp" in answer
    print(f"Verified new session retrieved episodic memory: {answer}")
