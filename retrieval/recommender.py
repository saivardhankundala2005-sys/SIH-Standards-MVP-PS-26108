import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import TOP_K, GRAPH_EXPANSION_HOPS, BASE_DIR, GOOGLE_API_KEY, API_KEYS_POOL
from ingestion.embedder import embed_query
from vectorstore.store import StandardsStore

CERT_MAPPING_PATH = BASE_DIR / "data" / "certification_mapping.json"
MODEL_FALLBACK_LIST = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-3.1-flash-lite", "gemini-1.5-pro"]


def _load_cert_rules():
    if not CERT_MAPPING_PATH.exists():
        return {"rules": [], "default": {"scheme": "Standard Verification Required", "authority": "BIS", "steps": []}}
    with open(CERT_MAPPING_PATH, encoding="utf-8") as f:
        return json.load(f)


def _lookup_certification(text_blob: str, cert_data: dict) -> dict:
    text_lower = text_blob.lower()
    for rule in cert_data.get("rules", []):
        if any(keyword.lower() in text_lower for keyword in rule["match_any"]):
            return {k: v for k, v in rule.items() if k != "match_any"}
    return cert_data.get("default", {})


def _normalize_is_number(is_num: str) -> str:
    cleaned = is_num.replace(" ", "").replace("-", "").upper()
    if not cleaned.startswith("IS"):
        cleaned = f"IS{cleaned}"
    return cleaned


def _get_api_keys(custom_key: Optional[str] = None) -> List[str]:
    keys = []
    if custom_key and custom_key.strip():
        keys.append(custom_key.strip())
    for k in API_KEYS_POOL:
        if k and k.strip() and k.strip() not in keys:
            keys.append(k.strip())
    if not keys and GOOGLE_API_KEY:
        keys.append(GOOGLE_API_KEY.strip())
    return keys


def _group_chunks_by_standard(query_result) -> Dict[str, Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = {}
    if not query_result or not query_result.get("ids") or not query_result["ids"][0]:
        return grouped

    ids = query_result["ids"][0]
    metadatas = query_result["metadatas"][0]
    documents = query_result["documents"][0]
    distances = query_result["distances"][0]

    for doc_id, md, doc, dist in zip(ids, metadatas, documents, distances):
        raw_is = md.get("is_number", "IS Unknown")
        norm_is = _normalize_is_number(raw_is)

        tech_params = []
        if md.get("technical_parameters_json"):
            try:
                tech_params = json.loads(md["technical_parameters_json"])
            except Exception:
                tech_params = []

        if norm_is not in grouped or dist < grouped[norm_is]["distance"]:
            grouped[norm_is] = {
                "is_number": raw_is,
                "norm_is_number": norm_is,
                "title": md.get("title", ""),
                "sector": md.get("sector", ""),
                "revision": md.get("revision", md.get("year", "")),
                "latest_amendment": md.get("latest_amendment", "0"),
                "source_url": md.get("source_url", ""),
                "normative_references": [r.strip() for r in md.get("normative_references", "").split(",") if r.strip()],
                "ocr_confidence": md.get("ocr_confidence", 1.0),
                "distance": float(dist),
                "snippet": doc[:280],
                "match_type": "primary",
                "technical_parameters": tech_params,
            }
    return grouped


def translate_query_to_english(query: str, api_key: Optional[str] = None, *args, **kwargs) -> str:
    keys = _get_api_keys(api_key)
    if not keys:
        return query

    prompt = f"Translate the following product description or procurement specification into clear, standard English for an Indian Standards search engine. Return ONLY the translated text without commentary.\n\nInput: {query}"

    for key in keys:
        try:
            import google.generativeai as genai
            genai.configure(api_key=key)
            for model_name in MODEL_FALLBACK_LIST:
                try:
                    model = genai.GenerativeModel(model_name)
                    resp = model.generate_content(prompt)
                    if resp.text and len(resp.text.strip()) > 3:
                        return resp.text.strip()
                except Exception:
                    continue
        except Exception as e:
            print(f"[warn] Translation notice with key {key[:8]}...: {e}")
            continue

    return query


def recommend(query: str, top_k: int = TOP_K, sector_filter: str | None = None, api_key: Optional[str] = None, *args, **kwargs) -> List[Dict[str, Any]]:
    store = StandardsStore()
    cert_data = _load_cert_rules()

    q_embedding = embed_query(query, api_key=api_key)
    where = {"sector": sector_filter} if sector_filter else None
    raw_results = store.query(q_embedding, top_k=top_k, where=where)

    primary = _group_chunks_by_standard(raw_results)

    all_results = dict(primary)
    frontier = set()
    for entry in primary.values():
        frontier.update([_normalize_is_number(r) for r in entry["normative_references"]])

    hops_done = 0
    while frontier and hops_done < GRAPH_EXPANSION_HOPS:
        next_frontier = set()
        for ref_is_number in frontier:
            if ref_is_number in all_results:
                continue
            ref_data = store.get_by_is_number(ref_is_number)
            if not ref_data or not ref_data.get("ids"):
                continue
            md = ref_data["metadatas"][0]
            display_is = md.get("is_number", ref_is_number)

            tech_params = []
            if md.get("technical_parameters_json"):
                try:
                    tech_params = json.loads(md["technical_parameters_json"])
                except Exception:
                    tech_params = []

            all_results[ref_is_number] = {
                "is_number": display_is,
                "norm_is_number": ref_is_number,
                "title": md.get("title", ""),
                "sector": md.get("sector", ""),
                "revision": md.get("revision", md.get("year", "")),
                "latest_amendment": md.get("latest_amendment", "0"),
                "source_url": md.get("source_url", ""),
                "normative_references": [r.strip() for r in md.get("normative_references", "").split(",") if r.strip()],
                "ocr_confidence": md.get("ocr_confidence", 1.0),
                "distance": None,
                "snippet": md.get("title", "") + " (Normative reference standard)",
                "match_type": "allied/normative reference",
                "technical_parameters": tech_params,
            }
            for sub_ref in md.get("normative_references", "").split(","):
                if sub_ref.strip():
                    next_frontier.add(_normalize_is_number(sub_ref.strip()))
        frontier = next_frontier - set(all_results.keys())
        hops_done += 1

    for entry in all_results.values():
        text_blob = f"{query} {entry['title']} {entry['sector']}"
        entry["certification"] = _lookup_certification(text_blob, cert_data)

    ranked = sorted(
        all_results.values(),
        key=lambda e: (e["match_type"] != "primary", e["distance"] if e["distance"] is not None else 999),
    )
    return ranked


def generate_rag_report(query: str, recommendations: List[Dict[str, Any]], api_key: Optional[str] = None, *args, **kwargs) -> str:
    keys = _get_api_keys(api_key)
    if not keys:
        return "*Technical report generation requires a valid API key configuration.*"

    context_lines = []
    for r in recommendations[:8]:
        tech_param_summary = []
        for p in r.get("technical_parameters", []):
            tech_param_summary.append(f"{p['parameter']}: {p['prescribed_limit_range']} {p.get('unit', '')}")
        param_str = "; ".join(tech_param_summary) if tech_param_summary else "Standard specifications apply"

        context_lines.append(
            f"- [{r['match_type'].upper()}] {r['is_number']} ({r['revision']}): {r['title']} | Sector: {r['sector']} | Latest Amd: {r['latest_amendment']} | Certification: {r['certification'].get('scheme', 'Standard')} | Prescribed Specifications: {param_str} | Normative Refs: {', '.join(r['normative_references'])}"
        )
    context_str = "\n".join(context_lines)

    prompt = f"""You are a Senior Public Procurement & Bureau of Indian Standards (BIS) Technical Auditor assisting procurement officials preparing technical specifications for government tenders.

Procurement Requirement / Product Description:
"{query}"

Applicable Indian Standards, Technical Parameters & Normative References:
{context_str}

Task: Generate a comprehensive, professional **Indian Standards Technical Procurement Specification Report**.

CRITICAL REQUIREMENT: Do NOT speak in vague generalities. You MUST include **exact numbers, quantitative ranges, numerical thresholds, safety limits, and measurement units** prescribed in the Indian Standards for the product being procured.

Do NOT mention any AI model, Gemini, RAG, or internal system names in the report body. Write as an official government technical compliance report.

Include the following structured sections:
1. **Executive Recommendation**: Summary of primary applicable Indian Standard(s) with revision & latest amendment details.
2. **Prescribed Technical Parameters & Safety Measurement Matrix (TABLE)**:
   Create a detailed Markdown Table with columns:
   | Technical Parameter / Property | Prescribed Numerical Limit / Range | Unit | Safety & Quality Significance | Prescribed Test / Verification |
   Provide to-the-point numbers (e.g. Operating Temp 90°C, Tensile Strength min 500 MPa, Dielectric Test 3000V, pH 6.5-8.5).
3. **Allied & Normative Reference Standards**: Explain why these referenced standards (e.g. testing methods, raw materials) must be included in the tender specification.
4. **Mandatory Certification & Statutory Compliance**: Detail mandatory ISI mark, CRS registration, or regulatory compliance (FSSAI, CDSCO, Hallmarking) along with compliance steps.
5. **Model Technical Tender Clause**: Provide a ready-to-paste technical specification paragraph containing the exact numerical limits that procurement officers can directly copy into tender documents.

Format in clean, authoritative GitHub Markdown with clear tables and bold numerical metrics.
"""

    last_error = ""
    for key in keys:
        try:
            import google.generativeai as genai
            genai.configure(api_key=key)
            for model_name in MODEL_FALLBACK_LIST:
                try:
                    model = genai.GenerativeModel(model_name)
                    resp = model.generate_content(prompt)
                    if resp.text:
                        return resp.text
                except Exception as m_err:
                    last_error = str(m_err)
                    continue
        except Exception as k_err:
            last_error = str(k_err)
            continue

    return f"*Could not generate report output ({last_error}). Please review standard specification tables below.*"
