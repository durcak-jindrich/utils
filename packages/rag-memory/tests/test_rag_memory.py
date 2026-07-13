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


def test_hybrid_search_and_reranking_internals():
    """Verify that hybrid search generates sparse vectors, queries the mock index correctly, and CrossEncoder rerank scores are applied."""
    from rag_memory.config import get_bm25_encoder, get_cross_encoder, get_pinecone_index
    from rag_memory.rag import query_documents
    
    # 1. Verify BM25 Encoder can encode queries and documents
    bm25 = get_bm25_encoder()
    # Fit it locally to test
    bm25.fit(["The quick brown fox", "jumps over the lazy dog", "Acme Corp contract renewal"])
    
    sparse_doc = bm25.encode_documents("Acme Corp renewal details")
    sparse_query = bm25.encode_queries("Acme Corp renewal")
    
    assert "indices" in sparse_doc and "values" in sparse_doc
    assert "indices" in sparse_query and "values" in sparse_query
    assert len(sparse_doc["indices"]) > 0
    assert len(sparse_query["indices"]) > 0

    # 2. Test MockCrossEncoder sorting logic
    cross_encoder = get_cross_encoder()
    # MockCrossEncoder uses word overlap to score
    pairs = [
        ("Acme Corp renewal", "Acme Corp contract renewal details on Monday"),
        ("Acme Corp renewal", "Some unrelated message about a different topic")
    ]
    scores = cross_encoder.predict(pairs)
    assert len(scores) == 2
    assert scores[0] > scores[1]  # The first one should have higher overlap score

    # 3. Test query_documents with fitted encoder and mock data
    index = get_pinecone_index()
    # Insert some dummy records into mock index with dense + sparse values
    # Dimension is 1536
    dummy_dense_1 = [0.1] * 1536
    dummy_dense_2 = [0.0] * 1536
    
    dummy_sparse_1 = bm25.encode_documents("Acme Corp contract renewal is on track")
    dummy_sparse_2 = bm25.encode_documents("Random unrelated chat about weather")
    
    vectors = [
        {
            "id": "doc_test_acme",
            "values": dummy_dense_1,
            "sparse_values": dummy_sparse_1,
            "metadata": {"text": "Acme Corp contract renewal is on track", "company": "Acme Corp"}
        },
        {
            "id": "doc_test_weather",
            "values": dummy_dense_2,
            "sparse_values": dummy_sparse_2,
            "metadata": {"text": "Random unrelated chat about weather", "company": "Other"}
        }
    ]
    index.upsert(vectors=vectors, namespace="documents")
    
    # Query for Acme Corp and verify we retrieve the Acme document first
    context = query_documents("Acme Corp renewal")
    assert "Acme Corp" in context
    assert context.startswith("Acme Corp")
