import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
from config import BASE_DIR, GOOGLE_API_KEY
from retrieval.recommender import recommend, translate_query_to_english, generate_rag_report
from ingestion.pdf_extractor import extract_text
from vectorstore.store import StandardsStore

# Page Config
st.set_page_config(
    page_title="Indian Standards Recommendation System — Department of Consumer Affairs",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar metadata & configuration
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg", width=60)
    st.markdown("### **Government of India**")
    st.markdown("**Department of Consumer Affairs (DoCA)**")
    st.caption("Ministry of Consumer Affairs, Food & Public Distribution")
    st.markdown("---")
    st.markdown("### **Problem Statement 26108**")
    st.markdown(
        "Recommendation Engine for Identifying Applicable Indian Standards for Procurement Specifications"
    )
    st.markdown("---")

    # API Key Configuration
    st.markdown("### **System Settings**")
    user_api_key = st.text_input(
        "API Access Key:",
        value=GOOGLE_API_KEY,
        type="password",
        help="Custom API Key configuration for specification analysis",
    )

    st.markdown("---")
    st.markdown("### **Appearance**")
    theme_choice = st.selectbox(
        "Theme Mode:",
        options=["Light Mode", "Dark Mode"],
        index=0,
        help="Select UI display theme (Light Mode is default)",
    )

# High-contrast CSS supporting both Light Mode and Dark Mode
if theme_choice == "Light Mode":
    st.markdown(
        """
        <style>
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #F8FAFC !important;
            color: #0F172A !important;
        }
        [data-testid="stSidebar"], [data-testid="stSidebar"] > div {
            background-color: #FFFFFF !important;
            border-right: 1px solid #E2E8F0 !important;
            color: #0F172A !important;
        }
        .main-title {
            font-size: 2.1rem;
            font-weight: 800;
            color: #1E3A8A !important;
            margin-bottom: 0.2rem;
            letter-spacing: -0.02em;
        }
        .sub-title {
            font-size: 1.05rem;
            color: #475569 !important;
            margin-bottom: 1.5rem;
        }
        .badge-primary {
            background-color: #D1FAE5 !important;
            color: #065F46 !important;
            border: 1px solid #10B981 !important;
            padding: 4px 12px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.85rem;
            display: inline-block;
        }
        .badge-allied {
            background-color: #DBEAFE !important;
            color: #1E40AF !important;
            border: 1px solid #3B82F6 !important;
            padding: 4px 12px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.85rem;
            display: inline-block;
        }
        .cert-box {
            background-color: #FEF3C7 !important;
            border-left: 4px solid #D97706 !important;
            color: #92400E !important;
            padding: 12px 16px;
            border-radius: 6px;
            margin-top: 10px;
            margin-bottom: 10px;
            font-size: 0.92rem;
            line-height: 1.5;
        }
        .cert-box b {
            color: #78350F !important;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """
        <style>
        /* Main background & view container */
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #0B0F19 !important;
            color: #F1F5F9 !important;
        }

        /* Sidebar styling */
        [data-testid="stSidebar"], [data-testid="stSidebar"] > div {
            background-color: #111827 !important;
            border-right: 1px solid #1E293B !important;
            color: #F1F5F9 !important;
        }
        [data-testid="stSidebar"] img, [data-testid="stSidebar"] [data-testid="stImage"] img {
            filter: brightness(0) invert(1) !important;
        }
        [data-testid="stSidebar"] * {
            color: #E2E8F0 !important;
        }
        [data-testid="stSidebar"] hr {
            border-color: #334155 !important;
        }

        /* Headers & Titles */
        .main-title {
            font-size: 2.1rem;
            font-weight: 800;
            color: #60A5FA !important;
            margin-bottom: 0.2rem;
            letter-spacing: -0.02em;
        }
        .sub-title {
            font-size: 1.05rem;
            color: #94A3B8 !important;
            margin-bottom: 1.5rem;
        }

        /* Typography, Paragraphs & Labels */
        p, span, label, h1, h2, h3, h4, h5, h6, [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li {
            color: #F1F5F9 !important;
        }
        [data-testid="stCaptionContainer"], small, caption {
            color: #94A3B8 !important;
        }

        /* Textarea, Input, Select, and File Uploader Boxes */
        textarea, input, 
        div[data-baseweb="input"], 
        div[data-baseweb="textarea"], 
        div[data-baseweb="select"] > div,
        [data-testid="stFileUploaderDropzone"] {
            background-color: #1E293B !important;
            color: #F8FAFC !important;
            border: 1px solid #334155 !important;
            border-radius: 8px !important;
        }
        textarea::placeholder, input::placeholder {
            color: #64748B !important;
        }
        div[data-baseweb="select"] * {
            background-color: #1E293B !important;
            color: #F8FAFC !important;
        }
        ul[role="listbox"] {
            background-color: #1E293B !important;
            border: 1px solid #334155 !important;
        }
        li[role="option"] {
            background-color: #1E293B !important;
            color: #F8FAFC !important;
        }
        li[role="option"]:hover, li[role="option"][aria-selected="true"] {
            background-color: #334155 !important;
            color: #60A5FA !important;
        }

        /* Buttons (Preset Buttons & Secondary Actions) */
        button:not([kind="primary"]), 
        .stButton > button:not([kind="primary"]),
        [data-testid="baseButton-secondary"] {
            background-color: #1E293B !important;
            color: #38BDF8 !important;
            border: 1px solid #334155 !important;
            border-radius: 6px !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
        }
        button:not([kind="primary"]):hover, 
        .stButton > button:not([kind="primary"]):hover {
            background-color: #334155 !important;
            border-color: #38BDF8 !important;
            color: #7DD3FC !important;
            box-shadow: 0 4px 12px rgba(56, 189, 248, 0.15) !important;
        }

        /* Primary Button */
        button[kind="primary"], .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
            color: #FFFFFF !important;
            border: none !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35) !important;
        }

        /* Containers, Cards & Expanders */
        [data-testid="stVerticalBlockBorderWrapper"],
        [data-testid="stExpander"] {
            background-color: #111827 !important;
            border: 1px solid #1E293B !important;
            border-radius: 8px !important;
            color: #F1F5F9 !important;
        }
        [data-testid="stExpander"] summary {
            color: #60A5FA !important;
            font-weight: 600 !important;
        }

        /* Tabs styling */
        [data-baseweb="tab-list"] {
            background-color: #111827 !important;
            border-bottom: 2px solid #1E293B !important;
            gap: 4px !important;
        }
        [data-baseweb="tab"] {
            color: #94A3B8 !important;
            font-weight: 600 !important;
            padding: 10px 16px !important;
            border-radius: 6px 6px 0 0 !important;
        }
        [data-baseweb="tab"][aria-selected="true"] {
            color: #60A5FA !important;
            background-color: #1E293B !important;
            border-bottom: 2px solid #60A5FA !important;
        }

        /* Metrics */
        [data-testid="stMetricValue"] {
            color: #38BDF8 !important;
        }
        [data-testid="stMetricLabel"] {
            color: #94A3B8 !important;
        }

        /* Badges & Alert boxes */
        .badge-primary {
            background-color: #064E3B !important;
            color: #A7F3D0 !important;
            border: 1px solid #059669 !important;
            padding: 4px 12px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.85rem;
            display: inline-block;
        }
        .badge-allied {
            background-color: #1E3A8A !important;
            color: #BFDBFE !important;
            border: 1px solid #2563EB !important;
            padding: 4px 12px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.85rem;
            display: inline-block;
        }
        .cert-box {
            background-color: rgba(217, 119, 6, 0.18) !important;
            border-left: 4px solid #F59E0B !important;
            color: #FDE68A !important;
            padding: 12px 16px;
            border-radius: 6px;
            margin-top: 10px;
            margin-bottom: 10px;
            font-size: 0.92rem;
            line-height: 1.5;
        }
        .cert-box b {
            color: #FBBF24 !important;
        }

        /* Dataframes & Tables */
        [data-testid="stDataFrame"], div[data-testid="stTable"] {
            background-color: #111827 !important;
            border: 1px solid #1E293B !important;
            border-radius: 8px !important;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

# Header
st.markdown('<div class="main-title">Indian Standards Recommendation System for Procurement Specifications</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Department of Consumer Affairs, Government of India — Technical Procurement Assistance</div>',
    unsafe_allow_html=True,
)

tab_search, tab_graph, tab_explorer, tab_cert = st.tabs([
    "Specification Analyzer & Recommendations",
    "Normative Reference Network",
    "Indian Standards Catalogue",
    "Quality Control & Statutory Certification Guide",
])

# Initialize session state for text area
if "query_input" not in st.session_state:
    st.session_state["query_input"] = ""

# ---------------------------------------------------------
# TAB 1: SPECIFICATION ANALYZER & RECOMMENDATIONS
# ---------------------------------------------------------
with tab_search:
    st.subheader("Technical Specification Analysis")

    # Helper function for sample presets
    def set_preset(preset_text: str):
        st.session_state["query_input"] = preset_text
        st.session_state["run_analysis"] = True

    st.caption("Sample procurement categories:")
    preset_cols = st.columns(5)
    if preset_cols[0].button("Armored Power Cables"):
        set_preset("Underground waterproof XLPE insulated copper power cable 1100V for municipal building")
    if preset_cols[1].button("Structural Steel & TMT Bars"):
        set_preset("High strength thermo-mechanically treated Fe 500D TMT steel reinforcement bars for concrete bridge")
    if preset_cols[2].button("Packaged Drinking Water"):
        set_preset("Packaged drinking bottled water supply for government canteen with FSSAI testing compliance")
    if preset_cols[3].button("Fire Extinguishers"):
        set_preset("Portable 6kg ABC dry powder fire extinguishers for office building installation and maintenance")
    if preset_cols[4].button("BWR Grade Plywood"):
        set_preset("Boiling water resistant BWR plywood 19mm for interior modular workstations")

    col_left, col_right = st.columns([3, 1])
    with col_left:
        query_input = st.text_area(
            "Enter product description, technical requirements, or paste tender text:",
            key="query_input",
            placeholder="e.g., Underground 1.1kV copper cable, waterproof sheathing, flame retardant PVC...",
            height=120,
        )

    with col_right:
        st.markdown("**Domain Restriction**")
        sector_filter = st.selectbox(
            "Restrict to Sector (Optional):",
            [
                "All Sectors",
                "Electrical & Cables",
                "Steel & Metallurgy",
                "Steel & Construction",
                "Building Materials & Civil Engineering",
                "Cement & Building Materials",
                "Water & Sanitation",
                "Food & Water",
                "Pipes & Water Distribution",
                "Timber & Building Materials",
                "Electronics & IT",
                "Fire Safety & Protection",
                "Medical Devices & Healthcare",
                "Automotive & Transport",
                "Space & Defence Industry",
            ],
        )

    uploaded_doc = st.file_uploader("Upload Tender Specification Document (PDF / TXT):", type=["pdf", "txt"])

    if uploaded_doc:
        if uploaded_doc.type == "application/pdf":
            temp_path = BASE_DIR / "uploads" / uploaded_doc.name
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            with open(temp_path, "wb") as f:
                f.write(uploaded_doc.getbuffer())
            text, _ = extract_text(temp_path)
            st.session_state["query_input"] = text[:1500]
            st.info(f"Extracted specification text from file '{uploaded_doc.name}' ({len(text)} characters)")

    analyze_button_clicked = st.button("Analyze Specification and Recommend Standards", type="primary")

    should_run = analyze_button_clicked or st.session_state.get("run_analysis", False)
    if "run_analysis" in st.session_state:
        del st.session_state["run_analysis"]

    if should_run:
        current_query = st.session_state.get("query_input", "").strip()
        if not current_query:
            st.warning("Please enter a product description or upload a document.")
        else:
            with st.spinner("Analyzing technical specification and identifying applicable standards..."):
                processed_query = translate_query_to_english(current_query, api_key=user_api_key)
                sec_filter = None if sector_filter == "All Sectors" else sector_filter
                results = recommend(processed_query, top_k=8, sector_filter=sec_filter, api_key=user_api_key)

            if not results:
                st.warning("No matching standards found in catalogue for the given specification.")
            else:
                # 1. Technical Procurement Report Section
                st.markdown("---")
                st.markdown("### Technical Procurement Specification Report")
                with st.spinner("Generating quantitative compliance report..."):
                    report_text = generate_rag_report(processed_query, results, api_key=user_api_key)
                    if report_text.startswith("*Technical report generation requires") or report_text.startswith("*Could not generate report"):
                        st.info("💡 **API Key Notice**: Enter your Gemini API Access Key in the sidebar settings to generate full AI-powered technical procurement reports.")
                    st.markdown(report_text)

                    st.download_button(
                        label="Download Technical Procurement Report",
                        data=report_text,
                        file_name="Indian_Standards_Procurement_Report.md",
                        mime="text/markdown",
                    )

                # 2. Applicable Standards Section (Primary vs Secondary split)
                st.markdown("---")
                st.markdown("### Applicable Indian Standards")

                primary_matches = [r for r in results if r["match_type"] == "primary"]
                secondary_matches = [r for r in results if r["match_type"] != "primary"]

                # Display Primary Standards
                for r in primary_matches:
                    badge_html = '<span class="badge-primary">Primary Applicable Standard</span>'
                    with st.container(border=True):
                        st.markdown(
                            f"#### **{r['is_number']} : {r['title']}** &nbsp;&nbsp; {badge_html}",
                            unsafe_allow_html=True,
                        )

                        m_col1, m_col2, m_col3 = st.columns(3)
                        m_col1.metric("Sector", r["sector"])
                        m_col2.metric("Revision / Year", r["revision"] or "—")
                        m_col3.metric("Latest Amendment", r["latest_amendment"] or "0")

                        if r.get("snippet"):
                            st.caption(f"**Scope Summary:** {r['snippet']}")

                        # Technical Parameters Matrix
                        tech_params = r.get("technical_parameters", [])
                        if tech_params:
                            st.markdown("##### **Prescribed Technical Parameters & Safety Measurement Ranges:**")
                            param_rows = []
                            for p in tech_params:
                                param_rows.append({
                                    "Technical Parameter": p.get("parameter", ""),
                                    "Prescribed Limit / Range": p.get("prescribed_limit_range", ""),
                                    "Unit": p.get("unit", ""),
                                    "Safety & Testing Significance": p.get("safety_significance", ""),
                                })
                            st.dataframe(param_rows, use_container_width=True)

                        # Certification Panel
                        cert = r.get("certification", {})
                        if cert.get("scheme"):
                            st.markdown(
                                f'<div class="cert-box"><b>Quality Control Order Requirement:</b> {cert["scheme"]}<br/><b>Authority:</b> {cert.get("authority", "BIS")}</div>',
                                unsafe_allow_html=True,
                            )
                            if cert.get("steps"):
                                st.caption("**Compliance Formalities:** " + " -> ".join(cert["steps"]))

                        # Normative References
                        if r.get("normative_references"):
                            st.markdown(
                                f"**Normative & Cross-Referenced Standards:** `"
                                + "`, `".join(r["normative_references"])
                                + "`"
                            )

                        if r.get("source_url"):
                            st.markdown(f"[View Official Standard Details on BIS Portal]({r['source_url']})")

                # Secondary & Allied Standards Expander
                if secondary_matches:
                    st.markdown("---")
                    with st.expander(f"View Additional Related Standards ({len(secondary_matches)} Standards)", expanded=False):
                        for r in secondary_matches:
                            badge_html = '<span class="badge-allied">Allied / Normative Reference Standard</span>'
                            with st.container(border=True):
                                st.markdown(
                                    f"#### **{r['is_number']} : {r['title']}** &nbsp;&nbsp; {badge_html}",
                                    unsafe_allow_html=True,
                                )
                                s_col1, s_col2 = st.columns(2)
                                s_col1.metric("Sector", r["sector"])
                                s_col2.metric("Revision / Year", r["revision"] or "—")

                                tech_params = r.get("technical_parameters", [])
                                if tech_params:
                                    st.markdown("##### **Prescribed Technical Parameters:**")
                                    param_rows = []
                                    for p in tech_params:
                                        param_rows.append({
                                            "Technical Parameter": p.get("parameter", ""),
                                            "Prescribed Limit / Range": p.get("prescribed_limit_range", ""),
                                            "Unit": p.get("unit", ""),
                                        })
                                    st.dataframe(param_rows, use_container_width=True)

                                if r.get("source_url"):
                                    st.markdown(f"[View Official Standard Details on BIS Portal]({r['source_url']})")

# ---------------------------------------------------------
# TAB 2: NORMATIVE REFERENCE NETWORK
# ---------------------------------------------------------
with tab_graph:
    st.subheader("Normative Standards Inter-Connection Network")
    st.write(
        "Indian Standards reference normative standards for testing procedures, safety requirements, and raw material quality. "
        "The view below details structural relationships between primary specifications and reference standards."
    )

    query_graph = st.text_input("Enter category or IS number to inspect normative network:", value="Electrical Cable")
    if st.button("Generate Network View"):
        results_graph = recommend(query_graph, top_k=5, api_key=user_api_key)
        if results_graph:
            st.markdown("#### **Standards Reference Tree**")
            for item in results_graph:
                if item["match_type"] == "primary":
                    st.markdown(f"**Primary Standard: {item['is_number']}** ({item['title']})")
                    if item.get("normative_references"):
                        for ref in item["normative_references"]:
                            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;└── Refers to: **{ref}** (Normative Test / Material Standard)")

# ---------------------------------------------------------
# TAB 3: INDIAN STANDARDS CATALOGUE
# ---------------------------------------------------------
with tab_explorer:
    st.subheader("Indian Standards Directory")
    st.write("Browse Indian Standards across key procurement sectors.")

    catalogue_file = BASE_DIR / "data" / "catalogue.json"
    if catalogue_file.exists():
        with open(catalogue_file, encoding="utf-8") as f:
            cat_data = json.load(f)

        search_term = st.text_input("Search standard by number, title, or sector:", "")
        filtered = [
            d for d in cat_data
            if search_term.lower() in d["is_number"].lower() or search_term.lower() in d["title"].lower() or search_term.lower() in d["sector"].lower()
        ]

        st.caption(f"Displaying {len(filtered)} of {len(cat_data)} indexed standards:")
        st.dataframe(
            filtered,
            column_order=["is_number", "title", "sector", "year", "latest_amendment", "certification_required"],
            use_container_width=True,
        )

# ---------------------------------------------------------
# TAB 4: STATUTORY CERTIFICATION GUIDE
# ---------------------------------------------------------
with tab_cert:
    st.subheader("Mandatory Certification & Quality Control Guide")
    st.markdown(
        """
        Public procurement in India mandates compliance with Quality Control Orders (QCOs) issued by Central Ministries under statutory provisions.
        
        #### **Mandatory Compliance Frameworks:**
        1. **BIS Product Certification Scheme (ISI Mark)**: Mandatory for electrical cables, structural steel, cement, plywood, fire extinguishers, and bottled water under respective Quality Control Orders. Requires ManakOnline registration, lab testing, and factory audit.
        2. **Compulsory Registration Scheme (CRS)**: Mandatory for 75+ electronics & IT goods (laptops, power banks, chargers, mobile phones). Requires self-declaration of conformity tested at BIS-recognized laboratories.
        3. **Hallmarking Scheme (HUID)**: Mandatory for gold and silver articles. Requires registration and Hallmark Unique ID verification.
        4. **FSSAI Food Safety Licence**: Mandatory for food items and packaged drinking water on the FoSCoS portal.
        5. **CDSCO Medical Device Registration**: Mandatory for medical devices under Medical Device Rules 2017 via the SUGAM portal.
        """
    )

# Footer
st.markdown("---")
st.caption(
    "Indian Standards Recommendation System | Department of Consumer Affairs, Ministry of Consumer Affairs, Food & Public Distribution, Government of India"
)
