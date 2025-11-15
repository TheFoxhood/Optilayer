# app.py
import streamlit as st
import pandas as pd
import anthropic
import json
import csv

st.set_page_config(page_title="OptiLayer", layout="centered")
st.title("OptiLayer v0.8 — Notion DB Cleaner")

# === FILE UPLOAD + SMART REFORMAT (v0.8) ===
uploaded_file = st.file_uploader("Upload CSV or XLSX", type=["csv", "xlsx"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file)
        else:
            # === SMART CSV REFORMATTER ===
            raw_text = uploaded_file.read().decode("utf-8")
            lines = raw_text.strip().split('\n')
            if not lines:
                st.error("Empty file.")
                st.stop()
                
            header_line = lines[0].strip()
            header = [h.strip('"') for h in header_line.split(',')]
            data_lines = lines[1:]
            
            clean_data = []
            for line in data_lines:
                line = line.strip()
                if not line:
                    continue
                values = line.split(',', len(header)-1)
                values = [v.strip('"') for v in values]
                clean_data.append(values[:len(header)])
            
            df = pd.DataFrame(clean_data, columns=header)
        
        if df.empty:
            st.error("No data found.")
            st.stop()
            
        # Initialize session state
        if 'clean_df' not in st.session_state:
            st.session_state.clean_df = df.copy()
        df = st.session_state.clean_df
        
    except Exception as e:
        st.error(f"Parse error: {e}")
        st.error("Fix: Save as CSV UTF-8. Quote fields with commas: \"Charlie, Jr\"")
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
        st.success("Empties dropped, blanks filled.")
        st.rerun()

    # === AI FIXES (v0.8 — DYNAMIC) ===
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

    # === APPLY AI FIXES ===
    if 'fixes' in st.session_state:
        st.success("AI Fixes Ready!")
        for fix in st.session_state.fixes:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"• {fix['title']}")
            with col2:
                if st.button("Apply", key=f"apply_{fix['id']}"):
                    try:
                        exec(fix["action"], {}, {"df": st.session_state.clean_df})
                        st.success("Applied!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed: {e}")

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
