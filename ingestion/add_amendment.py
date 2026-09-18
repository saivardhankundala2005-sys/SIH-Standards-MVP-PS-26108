"""
Adds ONE amendment/new-revision PDF to the existing vector base without
touching anything else. This is the function called both from the CLI and
from the API's /upload_amendment endpoint.

CLI: python -m ingestion.add_amendment --pdf path/to/file.pdf --is_number 2062 --revision 2024_Amd3
"""
import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from ingestion.pdf_extractor import extract_text, extract_normative_references
from ingestion.chunker import chunk_text
from ingestion.embedder import embed_texts
from vectorstore.store import StandardsStore


def add_amendment(pdf_path: str, is_number: str, revision: str,
                   title: str = "", sector: str = "", source_url: str = "") -> dict:
    text, ocr_confidence = extract_text(Path(pdf_path))
    if not text.strip():
        return {"ok": False, "error": "No extractable text (scan quality too low even for OCR)."}

    normative_refs = extract_normative_references(text)
    chunks = chunk_text(text)
    if not chunks:
        return {"ok": False, "error": "No content to chunk."}
    embeddings = embed_texts(chunks)

    store = StandardsStore()
    # Reuse title/sector from the existing record if not explicitly given,
    # so an amendment upload doesn't need to repeat metadata.
    if not title or not sector:
        existing = store.get_by_is_number(is_number)
        if existing["metadatas"]:
            title = title or existing["metadatas"][0].get("title", "")
            sector = sector or existing["metadatas"][0].get("sector", "")

    store.upsert_standard_chunks(
        is_number=is_number,
        revision=revision,
        chunks=chunks,
        embeddings=embeddings,
        base_metadata={
            "title": title or is_number,
            "sector": sector or "Unclassified",
            "year": revision,
            "source_url": source_url,
            "normative_references": ",".join(normative_refs),
            "ocr_confidence": ocr_confidence,
            "latest_amendment": revision,
        },
        is_amendment=True,
    )
    return {"ok": True, "is_number": is_number, "revision": revision,
            "chunks_added": len(chunks), "normative_references": normative_refs}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--is_number", required=True)
    parser.add_argument("--revision", default="latest")
    parser.add_argument("--title", default="")
    parser.add_argument("--sector", default="")
    args = parser.parse_args()

    result = add_amendment(args.pdf, args.is_number, args.revision, args.title, args.sector)
    print(result)


if __name__ == "__main__":
    main()
