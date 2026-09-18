# AI-Powered Recommendation Engine for Indian Standards (SIH PS 26108)

[![Smart India Hackathon](https://img.shields.io/badge/SIH-2024%2F2025-orange.svg)](https://www.sih.gov.in/)
[![Problem Statement](https://img.shields.io/badge/Problem%20Statement-PS--26108-blue.svg)]()
[![Team](https://img.shields.io/badge/Team-MindForge-brightgreen.svg)]()
[![Ministry](https://img.shields.io/badge/Ministry-Dept.%20of%20Consumer%20Affairs-red.svg)](https://consumeraffairs.nic.in/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)]()

> **Smart India Hackathon Solution**  
> **Problem Statement ID:** PS 26108 / PS 108  
> **Title:** Recommendation Engine for Identifying Applicable Indian Standards for Technical Procurement Specifications  
> **Organization:** Department of Consumer Affairs (DoCA), Ministry of Consumer Affairs, Food & Public Distribution  
> **Team Name:** **MindForge**  
> **Repository:** [SIH-Standards-MVP-PS-26108](https://github.com/saivardhankundala2005-sys/SIH-Standards-MVP-PS-26108)

---

## 🇮🇳 Executive Summary

In public procurement (e.g., GeM tenders, CPWD civil works, Indian Railways, Defence), identifying the exact, up-to-date **Bureau of Indian Standards (BIS)** specifications, normative references, and statutory **Quality Control Orders (QCOs)** is crucial for quality assurance and compliance.

**MindForge** presents an end-to-end, AI-driven recommendation and intelligence engine that automatically maps plain-language product descriptions, category queries, or full tender specification documents to:
1. **Primary Applicable Indian Standards (IS)** with exact version numbers and titles.
2. **Normative & Cross-Referenced Standards** (material specs, safety standards, testing methods).
3. **Latest Amendment Status** with real-time vector upsert capability for newly issued amendments without rebuilding vector indexes.
4. **Mandatory Statutory Certification Requirements** (BIS ISI Mark, Compulsory Registration Scheme (CRS), Hallmarking, FSSAI, CDSCO).
5. **Technical Procurement Reports** with automated compliance summaries and parameter matrices.

---

## 🏗️ System Architecture

```
                 ┌─────────────────────────────────────────┐
                 │            Data Sources (BIS)            │
                 │  Know Your Standard | Catalogue-by-Sector │
                 │  Product Manuals | Dept POW PDFs | CDSCO  │
                 │  FSSAI | e-books                          │
                 └───────────────┬───────────────────────────┘
                                 │  scrape / bulk download (one-time + scheduled)
                                 ▼
                 ┌─────────────────────────────────────────┐
                 │   Ingestion Pipeline (ingestion/)         │
                 │  1. pdf_extractor: text + tables + OCR    │
                 │  2. chunker: section-aware chunks + meta  │
                 │     (IS no., title, sector, year, status) │
                 │  3. embedder: text -> vector               │
                 └───────────────┬───────────────────────────┘
                                 ▼
                 ┌─────────────────────────────────────────┐
                 │   Vector Store (vectorstore/store.py)     │
                 │  Chroma (persisted) — collection          │
                 │  "indian_standards", metadata filters,    │
                 │  upsert by IS-number+revision so          │
                 │  amendments REPLACE old chunks seamlessly │
                 └───────────────┬───────────────────────────┘
                                 ▼
                 ┌─────────────────────────────────────────┐
                 │  Recommendation Engine (retrieval/)       │
                 │  1. embed user query (product desc/spec)  │
                 │  2. top-k semantic search                 │
                 │  3. expand via normative-reference graph  │
                 │     (allied/cross-referenced standards)   │
                 │  4. attach certification rules            │
                 │     (BIS/CRS/Hallmarking lookup table)    │
                 │  5. flag superseded versions -> latest     │
                 └───────────────┬───────────────────────────┘
                                 ▼
                 ┌─────────────────────────────────────────┐
                 │   API (api/main.py, FastAPI)              │
                 │  POST /recommend                          │
                 │  POST /upload_amendment  (incremental)     │
                 │  GET  /standard/{is_no}                   │
                 └───────────────┬───────────────────────────┘
                                 ▼
                 ┌─────────────────────────────────────────┐
                 │   UI (ui/app.py, Streamlit)               │
                 │  - text box: describe product / category  │
                 │  - OR upload tender document              │
                 │  - results: primary & allied IS cards,    │
                 │    revision status, QCO requirements,      │
                 │    normative reference tree               │
                 │  - Live "Add Amendment" PDF uploader       │
                 └─────────────────────────────────────────┘
```

---

## ⭐ Key Innovations & Highlights

- **Semantic Vector Search (Not Simple Keyword Search):** Uses Google Gemini (`text-embedding-004`) embeddings and Chroma DB vector store. A search for *"waterproof armored cable"* correctly identifies **IS 694** / **IS 7098** even if the query doesn't match verbatim terms.
- **Normative Reference Expansion Graph:** Automatically extracts and links normative reference standards mentioned in front matter. Recommending **IS 2062** (Structural Steel) automatically surfaces **IS 1608** (Tensile Testing) and **IS 8910** (Technical Delivery Requirements).
- **In-Place Dynamic Amendment Updates:** Individual standard chunks are upserted with unique IDs (`IS_NUMBER_REVISION_CHUNKIDX`). Uploading `IS_2062_2011_Amd3.pdf` updates metadata on the existing standard record instantly without re-indexing the entire database.
- **Deterministic Statutory Certification Mapping:** Integrates a structured QCO matrix (`data/certification_mapping.json`) mapping product categories to mandatory BIS ISI licensing, CRS electronics registration, HUID hallmarking, FSSAI, or CDSCO compliance.
- **Multilingual Support:** Queries in regional Indian languages are auto-translated into English prior to embedding, matching canonical published standards text.
- **Automated Technical Procurement Report Generation:** Generates downloadable Markdown compliance reports detailing applicable standards, technical parameter limits, and certification steps.

---

## 📁 Directory Structure

```
.
├── api/
│   └── main.py                   # FastAPI REST API endpoints
├── data/
│   ├── catalogue.json            # Indexed Indian Standards catalogue database
│   ├── catalogue_manual_template.csv # Manual input template for standard insertion
│   └── certification_mapping.json# Quality Control Order (QCO) statutory mapping rules
├── ingestion/
│   ├── add_amendment.py          # Dynamic single-PDF amendment ingestion script
│   ├── build_index.py            # Bulk indexing script for Chroma vector store
│   ├── chunker.py                # Section-aware text chunking utility
│   ├── embedder.py               # Embedding backend integration (Gemini / SentenceTransformers)
│   └── pdf_extractor.py          # PDF text and table extraction engine
├── retrieval/
│   └── recommender.py            # Semantic retrieval & graph expansion logic
├── scraper/
│   ├── bis_catalogue_scraper.py  # BIS web catalogue scraper
│   └── pdf_downloader.py         # Automated PDF downloader
├── storage/
│   └── chroma/                   # Persisted Chroma DB vector store
├── ui/
│   └── app.py                    # Streamlit interactive Web Interface
├── vectorstore/
│   └── store.py                  # Chroma DB vector database abstraction
├── .env.example                  # Environment configuration template
├── config.py                     # Global configuration & environment loader
├── requirements.txt              # Project Python dependencies
└── README.md                     # Project Documentation
```

---

## 🚀 Setup & Installation Guide

### Prerequisites
- Python 3.9+ installed
- Git installed
- Google Gemini API Key

### 1. Clone the Repository
```bash
git clone git@github.com:saivardhankundala2005-sys/SIH-Standards-MVP-PS-26108.git
cd SIH-Standards-MVP-PS-26108
```

### 2. Create a Virtual Environment & Install Dependencies
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the root directory (or copy from `.env.example`):
```bash
cp .env.example .env
```
Edit `.env` and set your API key:
```env
GOOGLE_API_KEY=your_google_gemini_api_key_here
EMBEDDING_BACKEND=gemini
```

---

## 🏃 Running the Application

### Option 1: Run the Interactive Web UI (Streamlit)
```bash
streamlit run ui/app.py
```
Access the application at `http://localhost:8501`.

### Option 2: Run the FastAPI REST Service
```bash
uvicorn api.main:app --reload --port 8000
```
Access API Interactive Swagger Documentation at `http://localhost:8000/docs`.

---

## 📑 Data Pipeline (Scraping & Ingestion)

If you wish to re-build or populate the vector database from scratch:

```bash
# 1. Scrape BIS Catalogue Metadata
python -m scraper.bis_catalogue_scraper --out data/catalogue.json

# 2. Download Product Manual PDFs listed in catalogue
python -m scraper.pdf_downloader --catalogue data/catalogue.json --out storage/pdfs/

# 3. Build & Populate Chroma Vector Index
python -m ingestion.build_index --pdf_dir storage/pdfs/ --catalogue data/catalogue.json
```

---

## 🔌 API Endpoint Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/recommend` | Submit product query / specification text to receive applicable standards & QCO compliance details |
| `POST` | `/upload_amendment` | Dynamically upload a new amendment PDF to update standard vector records live |
| `GET` | `/standard/{is_number}` | Retrieve indexing metadata and chunk count for a specific Indian Standard |
| `GET` | `/health` | API health check status |

### Example Request (`POST /recommend`)
```json
{
  "query": "Underground waterproof XLPE insulated copper power cable 1100V for municipal building",
  "sector_filter": "Electrical & Cables",
  "top_k": 8,
  "translate": true,
  "generate_report": true
}
```

---

## 🎯 SIH Hackathon Demo Script (2-3 Minutes)

1. **Category Search:** Enter a query such as *"underground waterproof power cable for government hospital"* → Engine retrieves **IS 694** & **IS 7098** (Primary), along with **IS 8130** (Conductor Testing) & **IS 5831** (PVC Insulation).
2. **Tender PDF Document Upload:** Upload a sample tender specification document → Engine extracts text automatically and generates recommendations.
3. **Statutory Certification Check:** System highlights mandatory **BIS ISI Mark / QCO Order** requirements for electrical cables automatically.
4. **Live Incremental Amendment Upload:** Upload a fresh amendment PDF (`IS_2062_Amd3.pdf`) via the UI → Re-run search to show the badge update to *"Latest Amendment: Amd 3"* without restarting servers.

---

## 👥 Team MindForge
Developed for **Smart India Hackathon (SIH)** under Problem Statement **PS-26108** for the **Department of Consumer Affairs (DoCA), Ministry of Consumer Affairs, Food & Public Distribution, Government of India**.

---
*Built with ❤️ by Team MindForge*
