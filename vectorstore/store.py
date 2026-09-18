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
        if self.collection.count() == 0:
            self._auto_seed()

    def _auto_seed(self):
        catalogue_path = Path(__file__).resolve().parent.parent / "data" / "catalogue.json"
        if not catalogue_path.exists():
            return
        try:
            import json
            from ingestion.chunker import chunk_text
            from ingestion.embedder import embed_texts
            with open(catalogue_path, encoding="utf-8") as f:
                records = json.load(f)
            print(f"[info] Auto-seeding vector database with {len(records)} standards...")
            for row in records:
                is_number = row.get("is_number", "").replace(" ", "").upper()
                title = row.get("title", "")
                sector = row.get("sector", "Unclassified")
                year = str(row.get("year", "2024"))
                description = row.get("description", "")
                norm_refs = row.get("normative_references", [])
                latest_amd = row.get("latest_amendment", "0")
                source_url = row.get("source_url", "")
                cert_req = row.get("certification_required", "")

                tech_params = row.get("technical_parameters", [])
                params_text_list = [f"{p['parameter']}: {p['prescribed_limit_range']} {p.get('unit', '')}" for p in tech_params]
                params_str = "; ".join(params_text_list)

                rich_text = f"Indian Standard {is_number}: {title}. Sector: {sector}. Year: {year}. Latest Amendment: {latest_amd}. Description: {description}. Technical Parameters & Safety Requirements: {params_str}. Certification: {cert_req}. Normative References: {', '.join(norm_refs)}"

                chunks = chunk_text(rich_text)
                if not chunks:
                    continue
                embeddings = embed_texts(chunks)

                self.upsert_standard_chunks(
                    is_number=is_number,
                    revision=year,
                    chunks=chunks,
                    embeddings=embeddings,
                    base_metadata={
                        "title": title,
                        "sector": sector,
                        "year": year,
                        "source_url": source_url,
                        "normative_references": ",".join(norm_refs),
                        "ocr_confidence": 1.0,
                        "latest_amendment": latest_amd,
                        "certification_required": cert_req,
                        "technical_parameters_json": json.dumps(tech_params),
                    },
                )
            print(f"[info] Vector database auto-seeded successfully!")
        except Exception as e:
            print(f"[warn] Auto-seeding vector store failed: {e}")

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
        count = self.collection.count()
        if count == 0:
            self._auto_seed()
            count = self.collection.count()

        if count == 0:
            return {"ids": [[]], "distances": [[]], "metadatas": [[]], "documents": [[]]}

        effective_k = min(top_k, count)
        base_dict = {"status": "active"}
        if where:
            base_dict.update(where)
        where_clause = _format_where(base_dict)

        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=effective_k,
            where=where_clause,
        )

    def get_by_is_number(self, is_number: str):
        if self.collection.count() == 0:
            self._auto_seed()
        where_clause = _format_where({"is_number": is_number, "status": "active"})
        return self.collection.get(where=where_clause)

