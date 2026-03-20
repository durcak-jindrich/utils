import os
from pathlib import Path
from .config import CHUNK_SIZE, CHUNK_OVERLAP
import logging

logger = logging.getLogger(__name__)

class Ingestor:
    def __init__(self, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str):
        """Chunk text into overlapping parts."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunks.append(text[start:end])
            start += self.chunk_size - self.chunk_overlap
        return chunks

    def process_file(self, file_path: Path):
        """Process a single markdown file."""
        if file_path.suffix != ".md":
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            chunks = self.chunk_text(content)
            results = []
            for idx, chunk in enumerate(chunks):
                results.append({
                    "content": chunk,
                    "metadata": {
                        "source": str(file_path),
                        "chunk_id": idx
                    },
                    "id": f"{file_path.name}_{idx}"
                })
            return results
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return []

    def process_directory(self, dir_path: Path):
        """Recursively process all markdown files in a directory."""
        all_results = []
        for root, _, files in os.walk(dir_path):
            for file in files:
                if file.endswith(".md"):
                    all_results.extend(self.process_file(Path(root) / file))
        return all_results
