import pytest
from pathlib import Path
from local_rag.ingest import Ingestor
from local_rag.db import ChromaManager
from unittest.mock import MagicMock

def test_ingestor_chunking():
    ingestor = Ingestor(chunk_size=10, chunk_overlap=2)
    text = "Hello world this is a test"
    chunks = ingestor.chunk_text(text)
    assert len(chunks) > 1
    assert "Hello worl" in chunks[0]

def test_process_file(tmp_path):
    d = tmp_path / "docs"
    d.mkdir()
    f = d / "test.md"
    f.write_text("This is a test document about RAG.")
    
    ingestor = Ingestor()
    results = ingestor.process_file(f)
    
    assert len(results) == 1
    assert results[0]["content"] == "This is a test document about RAG."
    assert results[0]["metadata"]["source"] == str(f)

def test_chroma_manager(tmp_path):
    db_path = str(tmp_path / "test_db")
    manager = ChromaManager(db_path=db_path)
    
    chunks = ["test chunk 1", "test chunk 2"]
    ids = ["id1", "id2"]
    metadata = [{"source": "file1"}, {"source": "file2"}]
    embeddings = [[0.1] * 384, [0.2] * 384] # Mock 384-dim embeddings
    
    manager.add_chunks(chunks, ids, metadata, embeddings)
    
    # Query with a mock embedding
    query_emb = [[0.11] * 384]
    results = manager.query(query_emb, n_results=1)
    
    assert results["documents"][0][0] == "test chunk 1"
    assert results["metadatas"][0][0]["source"] == "file1"
