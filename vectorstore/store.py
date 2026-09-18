"""
Wraps a persisted Chroma collection. Incremental update mechanism for amendments:

  - Every chunk's id is f"{is_number}_{revision}_{chunk_idx}".
  - When a new amendment/revision for the same is_number is ingested, we:
      1. mark all EXISTING chunks for that is_number as metadata status="superseded"
      2. add the NEW chunks with status="active" and bump latest_amendment/year
  - Recommendation queries filter on status="active" by default.
"""
import sys
from pathlib import Path
from typing import List, Dict, Any

sys.path.append(str(Path(__file__).resolve().parent.parent))

import chromadb
from config import CHROMA_DIR, COLLECTION_NAME


def _format_where(conditions: Dict[str, Any]) -> Dict[str, Any] | None:
    if not conditions:
        return None
    items = [{k: v} for k, v in conditions.items() if v is not None]
    if not items:
        return None
    if len(items) == 1:
        return items[0]
    return {"$and": items}


class StandardsStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def _mark_superseded(self, is_number: str):
        where_clause = _format_where({"is_number": is_number, "status": "active"})
        existing = self.collection.get(where=where_clause)
        if not existing or not existing.get("ids"):
            return
        updated_metadatas = []
        for md in existing["metadatas"]:
            md = dict(md)
            md["status"] = "superseded"
            updated_metadatas.append(md)
        self.collection.update(ids=existing["ids"], metadatas=updated_metadatas)

    def upsert_standard_chunks(
        self,
        is_number: str,
        revision: str,
        chunks: List[str],
        embeddings: List[List[float]],
        base_metadata: Dict[str, Any],
        is_amendment: bool = False,
    ):
        if is_amendment:
            self._mark_superseded(is_number)

        ids = [f"{is_number}_{revision}_{i}" for i in range(len(chunks))]
        metadatas = []
        for i in range(len(chunks)):
            md = dict(base_metadata)
            md.update({
                "is_number": is_number,
                "revision": revision,
                "status": "active",
                "chunk_index": i,
            })
            metadatas.append(md)

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
        )

    def query(self, query_embedding: List[float], top_k: int = 8, where: Dict[str, Any] | None = None):
        base_dict = {"status": "active"}
        if where:
            base_dict.update(where)
        where_clause = _format_where(base_dict)

        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_clause,
        )

    def get_by_is_number(self, is_number: str):
        where_clause = _format_where({"is_number": is_number, "status": "active"})
        return self.collection.get(where=where_clause)
