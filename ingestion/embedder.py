import sys
from pathlib import Path
from typing import List, Optional
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import EMBEDDING_BACKEND, GOOGLE_API_KEY, API_KEYS_POOL, LOCAL_EMBEDDING_MODEL

_local_model = None


def _get_local_model():
    global _local_model
    if _local_model is None:
        from sentence_transformers import SentenceTransformer
        _local_model = SentenceTransformer(LOCAL_EMBEDDING_MODEL)
    return _local_model


def embed_texts(texts: List[str], api_key: Optional[str] = None) -> List[List[float]]:
    active_keys = [api_key] if api_key and api_key.strip() else API_KEYS_POOL
    if not active_keys:
        active_keys = [GOOGLE_API_KEY]

    for key in active_keys:
        if not key.strip():
            continue
        try:
            import google.generativeai as genai
            genai.configure(api_key=key.strip())
            vectors = []
            for t in texts:
                resp = genai.embed_content(model="models/gemini-embedding-001", content=t)
                vectors.append(resp["embedding"])
            return vectors
        except Exception as e:
            print(f"[warn] Embedding failed with key {key[:8]}...: {e}")
            continue

    # Fallback to local model
    try:
        model = _get_local_model()
        return model.encode(texts, show_progress_bar=False).tolist()
    except Exception as e:
        print(f"[error] Local model fallback failed: {e}")
        return [[0.0] * 384 for _ in texts]


def embed_query(query: str, api_key: Optional[str] = None) -> List[float]:
    return embed_texts([query], api_key=api_key)[0]
