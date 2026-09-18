"""
One-time (or scheduled) bulk ingestion: reads every entry in catalogue.json AND
every PDF in --pdf_dir, matches metadata, extracts text, chunks, embeds,
and upserts into the vector store.

Run: python -m ingestion.build_index --pdf_dir storage/pdfs/ --catalogue data/catalogue.json
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from ingestion.pdf_extractor import extract_text, extract_normative_references
from ingestion.chunker import chunk_text
from ingestion.embedder import embed_texts
from vectorstore.store import StandardsStore

IS_NUMBER_IN_FILENAME = re.compile(r"IS[\s_\-]?(\d{2,6})", re.IGNORECASE)


def guess_is_number(filename: str) -> str:
    m = IS_NUMBER_IN_FILENAME.search(filename)
    return f"IS {m.group(1)}" if m else Path(filename).stem[:30]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf_dir", default="storage/pdfs")
    parser.add_argument("--catalogue", default="data/catalogue.json")
    args = parser.parse_args()

    store = StandardsStore()
    catalogue_path = Path(args.catalogue)

    # 1. Ingest standards from catalogue.json
    if catalogue_path.exists():
        print(f"Loading catalogue from {catalogue_path}...")
        with open(catalogue_path, encoding="utf-8") as f:
            records = json.load(f)

        print(f"Ingesting {len(records)} catalogue standards into vector database...")
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

            # Create rich text payload for semantic search
            rich_text = f"Indian Standard {is_number}: {title}. Sector: {sector}. Year: {year}. Latest Amendment: {latest_amd}. Description: {description}. Technical Parameters & Safety Requirements: {params_str}. Certification: {cert_req}. Normative References: {', '.join(norm_refs)}"

            chunks = chunk_text(rich_text)
            if not chunks:
                continue
            embeddings = embed_texts(chunks)

            store.upsert_standard_chunks(
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
            print(f"  [OK] Ingested {is_number} ({title[:35]}...) with {len(tech_params)} technical parameters")

    # 2. Ingest PDFs if present in pdf_dir
    pdf_paths = list(Path(args.pdf_dir).glob("*.pdf"))
    if pdf_paths:
        print(f"\nFound {len(pdf_paths)} PDFs to ingest from {args.pdf_dir}...")
        for pdf_path in pdf_paths:
            is_number = guess_is_number(pdf_path.name).replace(" ", "").upper()
            print(f"Ingesting PDF {pdf_path.name} -> {is_number}")
            text, ocr_confidence = extract_text(pdf_path)
            if not text.strip():
                print(f"  [warn] empty text extracted from PDF, skipping")
                continue

            normative_refs = extract_normative_references(text)
            chunks = chunk_text(text)
            if not chunks:
                continue
            embeddings = embed_texts(chunks)

            store.upsert_standard_chunks(
                is_number=is_number,
                revision="PDF",
                chunks=chunks,
                embeddings=embeddings,
                base_metadata={
                    "title": pdf_path.stem,
                    "sector": "PDF Upload",
                    "year": "2024",
                    "source_url": str(pdf_path),
                    "normative_references": ",".join(normative_refs),
                    "ocr_confidence": ocr_confidence,
                    "latest_amendment": "0",
                },
            )
            print(f"  -> {len(chunks)} chunks extracted from PDF")

    print("\nIndex build complete!")


if __name__ == "__main__":
    main()
