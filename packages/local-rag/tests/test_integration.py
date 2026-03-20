import pytest
import os
from pathlib import Path
from dotenv import load_dotenv
from local_rag.ai import AIHandler
from local_rag.db import ChromaManager
from local_rag.ingest import Ingestor

# Load .env to get the real API key
load_dotenv()

@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set in environment")
def test_real_gemini_integration(tmp_path):
    """
    Test the full flow with a real Gemini API call.
    This test will only run if GEMINI_API_KEY is present in the environment.
    """
    # Setup
    db_path = str(tmp_path / "integration_db")
    db_manager = ChromaManager(db_path=db_path)
    ai_handler = AIHandler()
    ingestor = Ingestor()

    # 1. Create a dummy doc
    doc_path = tmp_path / "architecture.md"
    doc_path.write_text("""
    # Project X Architecture
    Project X uses a microservices architecture.
    The primary database is PostgreSQL.
    The frontend is built with React and Tailwind CSS.
    It uses Gemini 1.5 Flash for its AI features.
    """)

    # 2. Ingest
    docs = ingestor.process_file(doc_path)
    contents = [d["content"] for d in docs]
    ids = [d["id"] for d in docs]
    metadatas = [d["metadata"] for d in docs]
    
    # This calls real sentence-transformers (local)
    embeddings = ai_handler.get_embeddings(contents)
    db_manager.add_chunks(contents, ids, metadatas, embeddings)

    # 3. Query
    query = "What is the primary database of Project X?"
    query_emb = ai_handler.get_embeddings([query])
    results = db_manager.query(query_emb, n_results=1)
    
    context = results["documents"][0][0]
    
    # 4. Generate Answer (Real API Call)
    answer = ai_handler.generate_answer(query, context)
    
    print(f"\nQuestion: {query}")
    print(f"Answer: {answer}")
    
    assert "PostgreSQL" in answer or "postgresql" in answer.lower()
    assert len(answer) > 10
