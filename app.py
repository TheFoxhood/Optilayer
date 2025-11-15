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

    # === AI FIXES ===
    if st.button("Generate AI Fixes"):
        with st.spinner("Analyzing with AI..."):
            try:
                client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
                sample = df.head(5).to_csv(index=False)
                prompt = f"""
                Analyze this Notion CSV:
                {sample}
                
                Suggest 3 actionable Pandas fixes (e.g., merge, fill, parse).
                Return JSON only:
                {{"fixes": [
                    {{"id": 1, "title": "Merge Name columns", "action": "df['Full Name'] = df['First Name'].fillna('') + ' ' + df['Last Name'].fillna('')"}},
                    {{"id": 2, "title": "Fill missing emails", "action": "df['Email'].fillna('unknown@example.com', inplace=True)"}},
                    {{"id": 3, "title": "Parse dates", "action": "df['Date'] = pd.to_datetime(df['Date'], errors='coerce')"}}
                ]}}
                """
                response = client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=300,
                    messages=[{"role": "user", "content": prompt}]
                )
                ai_output = response.content[0].text.strip()
                start = ai_output.find('{')
                end = ai_output.rfind('}') + 1
                fixes = json.loads(ai_output[start:end]).get("fixes", [])
                st.session_state.fixes = fixes
                st.rerun()
            except Exception as e:
                st.error(f"AI error: {e}")

    # === APPLY AI FIXES ===
    if 'fixes' in st.session_state:
        st.success("AI Fixes Generated!")
        for fix in st.session_state.fixes:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"• {fix['title']}")
            with col2:
                if st.button("Apply", key=f"apply_{fix['id']}"):
                    try:
                        exec(fix["action"], {}, {"df": st.session_state.clean_df})
                        st.success(f"Applied: {fix['title']}")
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
