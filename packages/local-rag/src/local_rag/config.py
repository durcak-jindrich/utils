import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project Paths
PACKAGE_ROOT = Path(__file__).parent.parent.parent
DEFAULT_DB_PATH = str(PACKAGE_ROOT / "chroma_db")

# AI Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
GEMINI_MODEL = "gemini-2.0-flash"

# Ingestion Settings
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
