# app.py
import streamlit as st
import pandas as pd
import anthropic
import json
import csv

st.set_page_config(page_title="OptiLayer", layout="centered")
st.title("OptiLayer v0.5.5 — Notion DB Cleaner")

# === FILE UPLOAD (CSV + XLSX) ===
uploaded_file = st.file_uploader("Upload CSV or XLSX", type=["csv", "xlsx"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            # Nuclear parser: skip bad lines, force quoting
            df = pd.read_csv(
                uploaded_file,
                on_bad_lines='skip',
                quoting=csv.QUOTE_ALL,
                engine='python'
            )
            if df.empty:
                st.warning("Bad lines skipped — data cleaned.")
                df = pd.DataFrame()
        else:
            df = pd.read_excel(uploaded_file)
        
        # Initialize clean state
        if 'clean_df' not in st.session_state:
            st.session_state.clean_df = df.copy()
        df = st.session_state.clean_df
        
    except Exception as e:
        st.error(f"Parse error: {e}")
        st.error("Fix: Quote fields with commas. Example: \"Charlie, Jr\"")
        st.stop()

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
        st.success("Raw data scrubbed: empties dropped, blanks filled.")
        st.rerun()

    # === AI FIXES (v0.6 — DYNAMIC) ===
    if st.button("Generate AI Fixes"):
        with st.spinner("Claude is analyzing your data..."):
            try:
                client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
                
                # Send REAL data + schema
                sample = st.session_state.clean_df.head(10).to_csv(index=False)
                columns = list(st.session_state.clean_df.columns)
                
                prompt = f"""
                You are a senior data engineer. Analyze this real Notion CSV:
                
                Data sample:
                {sample}
                
                Columns: {columns}
                
                Suggest 3 **actionable Pandas fixes** that:
                - Merge, clean, or reformat
                - Are safe to run
                - Use only existing columns
                
                Return JSON only:
                {{
                    "fixes": [
                        {{"id": 1, "title": "Merge 'Name' into 'Full Name'", "action": "df['Full Name'] = df['Name']"}},
                        {{"id": 2, "title": "Parse 'Date' to datetime", "action": "df['Date'] = pd.to_datetime(df['Date'], errors='coerce')"}},
                        {{"id": 3, "title": "Fill missing 'Status'", "action": "df['Status'].fillna('Unknown', inplace=True)"}}
                    ]
                }}
                """
                
                response = client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=400,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                raw = response.content[0].text.strip()
                start = raw.find('{')
                end = raw.rfind('}') + 1
                fixes = json.loads(raw[start:end])["fixes"]
                
                st.session_state.fixes = fixes
                st.rerun()
                
            except Exception as e:
                st.error(f"AI error: {e}")

        # === AI FIXES (v0.7 — BULLETPROOF) ===
        if st.button("Generate AI Fixes"):
            with st.spinner("Claude is analyzing your data..."):
                try:
                    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
                    
                    sample = st.session_state.clean_df.head(10).to_csv(index=False)
                    columns = list(st.session_state.clean_df.columns)
                    
                    prompt = f"""
                    Analyze this real Notion CSV:
                    {sample}
                    Columns: {columns}
                    
                    Suggest 3 actionable Pandas fixes using ONLY existing columns.
                    Return JSON only:
                    {{"fixes": [
                        {{"id": 1, "title": "Merge 'Name' into 'Full Name'", "action": "df['Full Name'] = df['Name']"}},
                        {{"id": 2, "title": "Parse 'Date'", "action": "df['Date'] = pd.to_datetime(df['Date'], errors='coerce')"}},
                        {{"id": 3, "title": "Fill 'Status'", "action": "df['Status'].fillna('Unknown', inplace=True)"}}
                    ]}}
                    """
                    
                    response = client.messages.create(
                        model="claude-3-haiku-20240307",
                        max_tokens=400,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    
                    raw = response.content[0].text.strip()
                    st.write("Raw AI Output:", raw)  # DEBUG
                    
                    start = raw.find('{')
                    end = raw.rfind('}') + 1
                    if start == -1 or end == 0:
                        st.error("AI returned invalid JSON.")
                        st.stop()
                        
                    fixes = json.loads(raw[start:end])["fixes"]
                    st.session_state.fixes = fixes
                    st.success("AI Fixes Ready!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"AI error: {e}")
                    st.write("Debug:", e)

    # === LIVE PREVIEW ===
    st.write("### Live Clean Data")
    st.dataframe(st.session_state.clean_df)

    # === DOWNLOAD ===
    csv_out = st.session_state.clean_df.to_csv(index=False).encode()
    st.download_button("Download Clean CSV", csv_out, "clean_notion_db.csv", "text/csv")

# === GUMROAD CTA ===
st.markdown("---")
st.markdown("### [Get Pro - $49 → AI + Apply + Export](https://mint2bmerry.gumroad.com/l/optilayer)")
st.caption("Built by @Mint2BMerry | Nov 15, 2025")
