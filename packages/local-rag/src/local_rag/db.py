import chromadb
from chromadb.config import Settings
from .config import DEFAULT_DB_PATH
import logging

logger = logging.getLogger(__name__)

class ChromaManager:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(
            name="local_docs",
            metadata={"description": "Chunks of markdown documents"}
        )

    def add_chunks(self, chunks: list[str], ids: list[str], metadata: list[dict], embeddings: list[list[float]]):
        """Add chunks to ChromaDB with their embeddings and metadata."""
        self.collection.add(
            documents=chunks,
            ids=ids,
            metadatas=metadata,
            embeddings=embeddings
        )
        logger.info(f"Added {len(chunks)} chunks to ChromaDB.")

    def query(self, query_embeddings: list[list[float]], n_results: int = 5):
        """Query ChromaDB for relevant chunks."""
        results = self.collection.query(
            query_embeddings=query_embeddings,
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        return results

    def clear(self):
        """Reset the database."""
        self.client.delete_collection("local_docs")
        self.collection = self.client.get_or_create_collection(name="local_docs")
        logger.info("ChromaDB cleared.")
