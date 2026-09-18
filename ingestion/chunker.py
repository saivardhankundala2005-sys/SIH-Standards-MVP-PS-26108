from typing import List
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import CHUNK_SIZE_CHARS, CHUNK_OVERLAP_CHARS


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_CHARS,
               overlap: int = CHUNK_OVERLAP_CHARS) -> List[str]:
    """Simple overlapping character-window chunker. Good enough for a
    hackathon MVP; swap for a section-heading-aware splitter (using the
    standard's numbered clause structure, e.g. '4. SCOPE', '5. REQUIREMENTS')
    if you have time before the final demo — it improves retrieval precision
    because a whole clause stays in one chunk."""
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
        if start <= 0:
            break
    return chunks
