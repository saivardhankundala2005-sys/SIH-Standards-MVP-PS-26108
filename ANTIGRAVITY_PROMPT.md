# Prompt for Google Antigravity

Paste this into Antigravity as your task/mission prompt, with the
`sih_standards_engine/` folder (from this deliverable) opened as the
workspace. Antigravity will use its agentic browser + editor + terminal
surfaces to extend and polish it.

---

**PROMPT:**

You are working in an existing Python project called `sih_standards_engine`
for Smart India Hackathon Problem Statement 26108: "AI-Powered Recommendation
Engine for Identifying Applicable Indian Standards for Procurement
Specifications" (Ministry of Consumer Affairs, Food & Public Distribution).

The project already has a working skeleton:
- `scraper/` — BIS catalogue + product-manual PDF scrapers
- `ingestion/` — PDF text extraction (with OCR fallback), chunking, embedding,
  full-index build script, and single-amendment incremental ingestion
- `vectorstore/store.py` — a Chroma-backed store where amendments upsert onto
  existing IS-number records (old chunks marked `status: superseded` rather
  than deleted or duplicated)
- `retrieval/recommender.py` — semantic search + normative-reference graph
  expansion (1-hop) + a deterministic certification-requirement lookup table
  (`data/certification_mapping.json`)
- `api/main.py` — FastAPI with `/recommend`, `/upload_amendment`, `/standard/{is_number}`
- `ui/app.py` — a Streamlit demo UI with a search tab and an amendment-upload tab

Read `README.md` first for the full architecture and rationale before
changing anything.

Your tasks, in priority order:

1. **Verify the environment.** Create a virtualenv, `pip install -r
   requirements.txt`, and confirm all modules import without error. Fix any
   version conflicts you hit (chromadb/sentence-transformers pin versions
   that sometimes clash with newer Python — resolve, don't just downgrade
   blindly).

2. **Populate a real starter vector base for the demo**, since BIS has no
   public bulk API and the scrapers are best-effort:
   - Use the `data/catalogue_manual_template.csv` (5 sample standards) as a
     starting catalogue — convert it to `data/catalogue.json` in the same
     shape the scraper would have produced.
   - For actual PDF content, either (a) attempt `scraper/pdf_downloader.py`
     against the live BIS product-manuals page and see what you can legally
     pull, or (b) if blocked/rate-limited, source 5-10 publicly available IS
     standard PDFs or summaries (cement, steel, cables, drinking water,
     structural steel are good demo picks — they have rich normative
     reference sections) and drop them in `storage/pdfs/` named like
     `IS_2062_2011.pdf` so the filename-based IS-number guesser in
     `ingestion/build_index.py` works.
   - Run `python -m ingestion.build_index --pdf_dir storage/pdfs/ --catalogue
     data/catalogue.json` and confirm the Chroma DB in `storage/chroma/` gets
     populated (print collection count as a sanity check).

3. **Improve normative-reference extraction accuracy.** The current
   `ingestion/pdf_extractor.py:extract_normative_references` is a naive regex
   scan for "IS <number>" patterns near a "Normative References" heading.
   Test it against 2-3 real IS PDFs and tune the regex / section-boundary
   heuristics if it's over- or under-matching. Add a unit test in
   `tests/test_pdf_extractor.py` with at least one real extracted sample.

4. **Wire up a section-aware chunker** as an upgrade to the naive
   character-window chunker in `ingestion/chunker.py`: split on numbered
   clause headings (e.g. "1. SCOPE", "2. NORMATIVE REFERENCES", "4.
   REQUIREMENTS") when they're detectable, falling back to the character
   window when they're not. Keep the existing function signature so nothing
   else needs to change.

5. **Add a lightweight evaluation harness**: a small JSON file of 8-10
   (query, expected_is_number) pairs a judge might plausibly ask (e.g.
   "waterproof cable for outdoor wiring" -> IS 694), and a script
   `eval/run_eval.py` that reports top-1 and top-3 hit rate against the
   current vector base. This is the single most convincing thing to show
   judges — a measured accuracy number, not just a live demo.

6. **Polish the Streamlit UI**: add a results-count summary at the top, a
   "why this standard" expander showing the matched snippet, and a sector
   filter dropdown populated dynamically from what's actually in the vector
   base (query distinct `sector` values from Chroma metadata) instead of a
   free-text box.

7. **Do NOT** invent fake BIS data, fake IS numbers, or fake certification
   rules to pad the demo — if a real source isn't available, leave a clearly
   marked TODO/placeholder and say so in your final summary rather than
   fabricating something that looks authoritative. This is a government
   compliance tool; incorrect standard numbers are the one thing that would
   actually harm someone if it shipped for real, so accuracy over
   completeness everywhere.

8. When done, give me: (a) a short summary of what you changed and why, (b)
   the eval harness's hit-rate numbers, (c) a list of anything still stubbed
   out (e.g. translation for multilingual queries) that I should mention as
   "future work" in the SIH pitch deck rather than claim as built.

Work incrementally, run the app after each major change to confirm it still
starts (`uvicorn api.main:app` and `streamlit run ui/app.py`), and keep
commits/diffs small enough for me to review.
