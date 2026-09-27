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


def _get_candidate_keys(api_key: Optional[str] = None) -> List[str]:
    import os
    keys = []
    if api_key and api_key.strip():
        keys.append(api_key.strip())
    for k in API_KEYS_POOL:
        if k and k.strip() and k.strip() not in keys:
            keys.append(k.strip())
    if GOOGLE_API_KEY and GOOGLE_API_KEY.strip() and GOOGLE_API_KEY.strip() not in keys:
        keys.append(GOOGLE_API_KEY.strip())
    env_key = os.getenv("GOOGLE_API_KEY", "")
    if env_key and env_key.strip() and env_key.strip() not in keys:
        keys.append(env_key.strip())
    return keys


def embed_texts(texts: List[str], api_key: Optional[str] = None) -> List[List[float]]:
    active_keys = _get_candidate_keys(api_key)

    for key in active_keys:
        try:
            import google.generativeai as genai
            genai.configure(api_key=key)
            vectors = []
            for t in texts:
                try:
                    resp = genai.embed_content(model="models/gemini-embedding-001", content=t)
                except Exception:
                    resp = genai.embed_content(model="models/text-embedding-004", content=t)
                vectors.append(resp["embedding"])
            return vectors
        except Exception as e:
            print(f"[warn] Gemini embedding failed with key {key[:8]}...: {e}")
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
