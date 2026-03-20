from google import genai
from sentence_transformers import SentenceTransformer
from .config import GEMINI_API_KEY, EMBEDDING_MODEL, GEMINI_MODEL
import logging

logger = logging.getLogger(__name__)

class AIHandler:
    def __init__(self):
        self._embedding_model = None
        self._client = None
        if GEMINI_API_KEY:
            self._client = genai.Client(api_key=GEMINI_API_KEY)
        else:
            logger.warning("GEMINI_API_KEY not found in environment. Answer generation will fail.")

    @property
    def embedding_model(self):
        if self._embedding_model is None:
            logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
            self._embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        return self._embedding_model

    def get_embeddings(self, texts: list[str]):
        """Generate embeddings for a list of texts."""
        return self.embedding_model.encode(texts).tolist()

    def generate_answer(self, query: str, context: str):
        """Generate an answer using Gemini based on the provided context."""
        if not self._client:
            return "Error: GEMINI_API_KEY is not set. Please add it to your .env file."

        prompt = f"""
        You are a helpful assistant answering questions about local documentation.
        Use the following retrieved context to answer the question.
        If the answer is not in the context, say that you don't know based on the provided documents.
        
        Context:
        {context}
        
        Question: {query}
        
        Answer:
        """
        response = self._client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        return response.text
