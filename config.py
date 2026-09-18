import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
CHROMA_DIR = STORAGE_DIR / "chroma"
PDF_DIR = STORAGE_DIR / "pdfs"
AMENDMENT_UPLOAD_DIR = BASE_DIR / "uploads" / "amendments"

for d in [STORAGE_DIR, CHROMA_DIR, PDF_DIR, AMENDMENT_UPLOAD_DIR]:
    d.mkdir(parents=True, exist_ok=True)

COLLECTION_NAME = "indian_standards"

EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "gemini")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
API_KEYS_POOL = [GOOGLE_API_KEY] if GOOGLE_API_KEY else []
LOCAL_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

CHUNK_SIZE_CHARS = 1200
CHUNK_OVERLAP_CHARS = 150

TOP_K = 6
GRAPH_EXPANSION_HOPS = 1
