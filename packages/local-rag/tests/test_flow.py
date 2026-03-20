import pytest
from pathlib import Path
from local_rag.ingest import Ingestor
from local_rag.db import ChromaManager
from local_rag.ai import AIHandler
from unittest.mock import MagicMock, patch

import numpy as np
@pytest.fixture
def mock_ai():
    with patch("local_rag.ai.SentenceTransformer") as mock_st:
        mock_model = MagicMock()
        # Mock embeddings to return numpy array which has .tolist()
        mock_model.encode.side_effect = lambda texts: np.array([[0.1] * 384 for _ in texts])
        mock_st.return_value = mock_model
        
        with patch("google.genai.Client") as mock_client:
            handler = AIHandler()
            yield handler, mock_model, mock_client

def test_full_flow_no_api(tmp_path, mock_ai):
    handler, mock_model, mock_client = mock_ai
    db_path = str(tmp_path / "test_db")
    db_manager = ChromaManager(db_path=db_path)
    ingestor = Ingestor()

    # 1. Create a doc
    doc_path = tmp_path / "test.md"
    doc_path.write_text("The secret password is 'pineapple'.")

    # 2. Ingest
    docs = ingestor.process_file(doc_path)
    contents = [d["content"] for d in docs]
    ids = [d["id"] for d in docs]
    metadatas = [d["metadata"] for d in docs]
    
    embeddings = handler.get_embeddings(contents)
    db_manager.add_chunks(contents, ids, metadatas, embeddings)

    # 3. Query
    query = "What is the secret password?"
    query_emb = handler.get_embeddings([query])
    results = db_manager.query(query_emb, n_results=1)

    assert results["documents"][0][0] == "The secret password is 'pineapple'."
    assert "test.md" in results["metadatas"][0][0]["source"]
