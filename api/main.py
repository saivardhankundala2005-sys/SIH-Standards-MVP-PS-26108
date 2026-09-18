import shutil
import sys
from pathlib import Path
from typing import Optional

sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel

from config import AMENDMENT_UPLOAD_DIR
from retrieval.recommender import recommend, translate_query_to_english, generate_rag_report
from ingestion.add_amendment import add_amendment
from vectorstore.store import StandardsStore

app = FastAPI(
    title="Indian Standards AI Recommendation Engine — SIH PS 26108",
    description="API for identifying applicable Indian Standards (BIS), normative references, latest amendments, and mandatory certification requirements for procurement specifications.",
    version="1.0.0",
)


class RecommendRequest(BaseModel):
    query: str
    sector_filter: Optional[str] = None
    top_k: int = 8
    translate: bool = True
    generate_report: bool = True


@app.post("/recommend")
def recommend_endpoint(req: RecommendRequest):
    processed_query = req.query
    if req.translate:
        processed_query = translate_query_to_english(req.query)

    results = recommend(processed_query, top_k=req.top_k, sector_filter=req.sector_filter)

    report = None
    if req.generate_report and results:
        report = generate_rag_report(processed_query, results)

    return {
        "original_query": req.query,
        "processed_query": processed_query,
        "results_count": len(results),
        "results": results,
        "rag_report": report,
    }


@app.post("/upload_amendment")
async def upload_amendment_endpoint(
    file: UploadFile = File(...),
    is_number: str = Form(...),
    revision: str = Form(...),
    title: str = Form(""),
    sector: str = Form(""),
):
    dest_path = AMENDMENT_UPLOAD_DIR / file.filename
    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    result = add_amendment(
        pdf_path=str(dest_path),
        is_number=is_number,
        revision=revision,
        title=title,
        sector=sector,
    )
    return result


@app.get("/standard/{is_number}")
def get_standard(is_number: str):
    store = StandardsStore()
    norm_is = is_number.replace(" ", "").upper()
    data = store.get_by_is_number(norm_is)
    if not data or not data.get("ids"):
        return {"found": False, "is_number": is_number}
    return {
        "found": True,
        "is_number": is_number,
        "metadata": data["metadatas"][0],
        "chunk_count": len(data["ids"]),
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "Indian Standards AI Recommendation Engine", "sih_ps": "26108"}
