import os
from pathlib import Path
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from langchain_core.embeddings import Embeddings
import hashlib
import numpy as np
import logging

# Configure logger
logger = logging.getLogger("rag_memory")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Find and load .env file from packages/rag-memory/ or parent
pkg_root = Path(__file__).resolve().parent.parent.parent
env_path = pkg_root / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
PINECONE_INDEX_NAME = os.environ.get("PINECONE_INDEX_NAME", "rag-memory-demo")


def is_placeholder(key: str) -> bool:
    """Check if the provided key is a placeholder or empty."""
    if not key:
        return True
    k = key.lower()
    return "placeholder" in k or "your_" in k or k == ""


class LocalDeterministicEmbeddings(Embeddings):
    """A self-contained embedding model that generates deterministic 1536-dim vectors.
    Useful for offline testing and when API keys are not provided.
    """
    def __init__(self, dimension: int = 1536):
        self.dimension = dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        # Generate a deterministic seed from the text hash
        h = hashlib.md5(text.encode("utf-8")).digest()
        seed = int.from_bytes(h, byteorder="big") % (2**32)
        rng = np.random.default_rng(seed)
        # Create a random vector of appropriate dimension
        vec = rng.normal(size=self.dimension)
        # Normalize to unit length (cosine similarity is dot product for unit vectors)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()


def get_embedding_model() -> Embeddings:
    """Return the embedding model based on active environment variables."""
    # Check if we should force mock embeddings
    if os.environ.get("MOCK_EMBEDDINGS", "false").lower() == "true":
        logger.info("Using local deterministic mock embeddings (forced by MOCK_EMBEDDINGS).")
        return LocalDeterministicEmbeddings()

    # Check if required keys are placeholders
    if is_placeholder(PINECONE_API_KEY):
        logger.info("PINECONE_API_KEY is a placeholder or empty. Using local deterministic mock embeddings.")
        return LocalDeterministicEmbeddings()

    # If OPENAI_API_KEY is present, we can use OpenAI
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if openai_key and not is_placeholder(openai_key):
        logger.info("Using OpenAIEmbeddings (text-embedding-3-small).")
        try:
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(model="text-embedding-3-small")
        except ImportError:
            pass

    # Default to Pinecone Inference embeddings if possible
    try:
        from langchain_pinecone import PineconeEmbeddings
        # Note: we use llama-text-embed-v2 or multilingual-e5-large.
        # Since Pinecone hosts e5-large, we can default to it.
        # But if we need 1536 dimension, let's hope the index dimensions are set to e.g. 1024 or 1536 is mocked.
        # If it is 1536, PineconeEmbeddings might fail unless it supports 1536.
        # Let's use llama-text-embed-v2 (or fallback).
        logger.info("Using PineconeEmbeddings from langchain-pinecone.")
        return PineconeEmbeddings(model="llama-text-embed-v2")
    except Exception as e:
        logger.warning(f"Failed to initialize PineconeEmbeddings: {e}. Falling back to local deterministic embeddings.")
        return LocalDeterministicEmbeddings()


def get_pinecone_client() -> Pinecone:
    """Return an initialized Pinecone client."""
    if is_placeholder(PINECONE_API_KEY):
        # Return a dummy client or raises error. We'll return client but handle mock operations
        return Pinecone(api_key="mock-api-key")
    return Pinecone(api_key=PINECONE_API_KEY)


_mock_index_instance = None


def get_pinecone_index():
    """Retrieve or create the Pinecone index, or return a mock index for testing."""
    global _mock_index_instance
    if is_placeholder(PINECONE_API_KEY):
        if _mock_index_instance is None:
            _mock_index_instance = MockPineconeIndex()
        logger.info("Using singleton MockPineconeIndex.")
        return _mock_index_instance
        
    pc = get_pinecone_client()
    
    # Check if index exists, create if not
    existing_indexes = pc.list_indexes().names()
    if PINECONE_INDEX_NAME not in existing_indexes:
        logger.info(f"Creating Pinecone index '{PINECONE_INDEX_NAME}' with dimension 1536.")
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )
    return pc.Index(PINECONE_INDEX_NAME)


class MockPineconeIndex:
    """A mock implementation of Pinecone index for testing when no real credentials are set."""
    def __init__(self):
        # Database structure: {namespace: {vector_id: {"values": list, "metadata": dict}}}
        self.db = {}

    def upsert(self, vectors, namespace):
        if namespace not in self.db:
            self.db[namespace] = {}
        
        for vec in vectors:
            vec_id = vec[0]
            values = vec[1]
            metadata = vec[2] if len(vec) > 2 else {}
            self.db[namespace][vec_id] = {
                "values": values,
                "metadata": metadata
            }
        logger.info(f"[Mock DB] Upserted {len(vectors)} vectors to namespace '{namespace}'")
        return {"upserted_count": len(vectors)}

    def query(self, vector, top_k, namespace, filter=None, include_metadata=True, include_values=False):
        logger.info(f"[Mock DB] Querying namespace '{namespace}' with filter={filter}")
        if namespace not in self.db:
            return {"matches": []}
            
        matches = []
        for vec_id, data in self.db[namespace].items():
            # Check metadata filter
            if filter:
                match_filter = True
                for f_key, f_val in filter.items():
                    # Support simple dict comparison
                    if isinstance(f_val, dict):
                        # Handle operator like $eq
                        if "$eq" in f_val:
                            if data["metadata"].get(f_key) != f_val["$eq"]:
                                match_filter = False
                        else:
                            # Unsupported complex filter in mock, default to True or False
                            pass
                    else:
                        if data["metadata"].get(f_key) != f_val:
                            match_filter = False
                if not match_filter:
                    continue
            
            # Simple cosine similarity (dot product of normalized vectors)
            v1 = np.array(vector)
            v2 = np.array(data["values"])
            similarity = float(np.dot(v1, v2))
            
            match = {
                "id": vec_id,
                "score": similarity,
            }
            if include_metadata:
                match["metadata"] = data["metadata"]
            if include_values:
                match["values"] = data["values"]
            matches.append(match)
            
        # Sort matches by similarity score descending
        matches.sort(key=lambda x: x["score"], reverse=True)
        return {"matches": matches[:top_k]}

    def delete(self, ids=None, delete_all=False, namespace=None):
        if namespace not in self.db:
            return {}
        if delete_all:
            self.db[namespace] = {}
            logger.info(f"[Mock DB] Deleted all vectors in namespace '{namespace}'")
        elif ids:
            for vec_id in ids:
                self.db[namespace].pop(vec_id, None)
            logger.info(f"[Mock DB] Deleted {len(ids)} vectors in namespace '{namespace}'")
        return {}
