# app.py
import streamlit as st
import pandas as pd
import anthropic
import json
import csv

st.set_page_config(page_title="dForge", layout="centered")
st.title("dForge v1.0 — Data Hygiene AI")

# === FILE UPLOAD + FULL REFRESH (v1.6) ===
uploaded_file = st.file_uploader("Upload CSV or XLSX", type=["csv", "xlsx"], key="file_uploader")

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file)
        else:
            # === SMART CSV PARSER ===
            raw_text = uploaded_file.read().decode("utf-8", errors="ignore")
            lines = raw_text.strip().split('\n')
            if not lines:
                st.error("Empty file.")
                st.stop()
                
            header = [h.strip('"') for h in lines[0].split(',')]
            data = []
            for line in lines[1:]:
                if not line.strip():
                    continue
                values = line.split(',', len(header)-1)
                values = [v.strip('"') for v in values]
                data.append(values[:len(header)])
            df = pd.DataFrame(data, columns=header)
        
        if df.empty:
            st.error("No data.")
            st.stop()
            
        # === FRESH STATE PER FILE ===
        st.session_state.clean_df = df.copy()
        st.session_state.current_file = uploaded_file.name
        
        # === CLEAR OLD AI FIXES ===
        if 'fixes' in st.session_state:
            del st.session_state.fixes
            
    except Exception as e:
        st.error(f"Parse error: {e}")
        st.stop()

# === SHOW CURRENT FILE ===
if 'current_file' in st.session_state:
    st.write(f"**Active File**: {st.session_state.current_file}")
    st.write("### Data Preview")
    st.dataframe(st.session_state.clean_df.head())
        
    # === DEBUG PANEL ===
    with st.expander("Debug: Raw Input"):
        uploaded_file.seek(0)
        st.text(uploaded_file.read().decode("utf-8", errors="ignore")[:1000])

    # === ORIGINAL DATA ===
    st.write("### Original Data")
    st.dataframe(df)

    # === METRICS ===
    total = len(df)
    dupes = df.duplicated().sum()
    st.metric("Dupe Rate", f"{dupes/total:.1%}" if total else "0%", f"{dupes} duplicates")

    # === 1-CLICK DEDUPE ===
    if st.button("Deduplicate Now"):
        clean_df = df.drop_duplicates()
        st.session_state.clean_df = clean_df
        st.success(f"Cleaned! {len(df) - len(clean_df)} rows removed.")
        st.rerun()

    # === CLEAN RAW DATA ===
    if st.button("Clean Raw Data"):
        st.session_state.clean_df = df.dropna().fillna('')
        st.success("Empties dropped, blanks filled.")
        st.rerun()

   # === AI FIXES (v1.7 — DEEP ANALYSIS) ===
if st.button("Generate AI Fixes"):
    with st.spinner("dForge is deeply analyzing your data..."):
        try:
            client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
            
            # === SEND FULL DATA + SCHEMA ===
            full_csv = st.session_state.clean_df.to_csv(index=False)
            stats = {
                "rows": len(st.session_state.clean_df),
                "columns": list(st.session_state.clean_df.columns),
                "nulls": st.session_state.clean_df.isna().sum().to_dict(),
                "dtypes": st.session_state.clean_df.dtypes.apply(lambda x: x.name).to_dict(),
                "sample": st.session_state.clean_df.head(3).to_csv(index=False)
            }
            
            prompt = f"""
            You are a senior data enrichment engineer.
            Analyze this FULL CSV and metadata:
            
            Full data (up to 1000 rows):
            {full_csv[:20000]}  # Truncate if huge
            
            Metadata:
            - Rows: {stats['rows']}
            - Columns: {stats['columns']}
            - Nulls per column: {stats['nulls']}
            - Data types: {stats['dtypes']}
            - Sample:
            {stats['sample']}
            
            Suggest 3 HIGH-VALUE, EXECUTABLE Pandas fixes:
            1. Clean & standardize (e.g., emails, phones, addresses)
            2. Enrich (e.g., extract domain, geocode city, add category)
            3. Structure (e.g., split name, parse date, normalize units)
            
            Use ONLY existing columns.
            Return JSON only:
            {{"fixes": [
                {{"id": 1, "title": "Standardize emails", "action": "df['Email'] = df['Email'].str.lower().str.strip().str.replace(' ', '')"}},
                {{"id": 2, "title": "Extract domain", "action": "df['Domain'] = df['Email'].str.split('@').str[-1]"}},
                {{"id": 3, "title": "Parse full name", "action": "df['First'] = df['Name'].str.split().str[0]; df['Last'] = df['Name'].str.split().str[-1]"}}
            ]}}
            """
            
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}]
            )
            
            raw = response.content[0].text.strip()
            start = raw.find('{')
            end = raw.rfind('}') + 1
            fixes = json.loads(raw[start:end])["fixes"]
            
            st.session_state.fixes = fixes
            st.success(f"AI Generated {len(fixes)} High-Value Fixes!")
            st.rerun()
            
        except Exception as e:
            st.error(f"AI error: {e}")
            
 # === APPLY FIXES (v1.7) ===
if 'fixes' in st.session_state:
    st.success(f"AI Fixes Ready ({len(st.session_state.fixes)})")
    for fix in st.session_state.fixes:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"• {fix['title']}")
        with col2:
            if st.button("Apply", key=f"apply_{fix['id']}"):
                try:
                    exec(fix["action"], {"pd": pd}, {"df": st.session_state.clean_df})
                    st.success("Applied!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed: {e}")
                    
    # === LIVE PREVIEW ===
    st.write("### Live Clean Data")
    st.dataframe(st.session_state.clean_df)

    # === DOWNLOAD ===
    csv_out = st.session_state.clean_df.to_csv(index=False).encode()
    st.download_button("Download Clean CSV", csv_out, "dforge_clean.csv", "text/csv")

# === GUMROAD CTA ===
st.markdown("---")
st.markdown("### [Get dForge → AI + Apply + Export](https://mint2bmerry.gumroad.com/l/dforge)")
st.caption("Built by @Mint2BMerry | Nov 15, 2025")
