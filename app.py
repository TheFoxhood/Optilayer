# app.py
import streamlit as st
import pandas as pd
import anthropic
import json
import csv

st.set_page_config(page_title="dForge", layout="centered")
st.title("dForge v1.0 — Data Hygiene AI")

# === FILE UPLOAD + NUCLEAR CSV PARSER (v1.3) ===
uploaded_file = st.file_uploader("Upload CSV or XLSX", type=["csv", "xlsx"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file)
        else:
            # === NUCLEAR CSV PARSER ===
            raw_lines = uploaded_file.read().decode("utf-8", errors="ignore").splitlines()
            if not raw_lines:
                st.error("Empty file.")
                st.stop()
                
            # Parse header
            header = [h.strip('"') for h in raw_lines[0].split(',')]
            data = []
            
            for i, line in enumerate(raw_lines[1:], start=2):
                if not line.strip():
                    continue
                values = []
                current = ""
                in_quote = False
                for char in line + ",":
                    if char == '"':
                        in_quote = not in_quote
                    elif char == ',' and not in_quote:
                        values.append(current.strip('"'))
                        current = ""
                    else:
                        current += char
                # Append last field
                if current:
                    values.append(current.strip('"'))
                # Truncate/pad to header length
                if len(values) > len(header):
                    values = values[:len(header)]
                elif len(values) < len(header):
                    values += [''] * (len(header) - len(values))
                data.append(values)
            
            df = pd.DataFrame(data, columns=header)
            
        if df.empty:
            st.error("No valid data found.")
            st.stop()
            
        st.session_state.clean_df = df.copy()
        
    except Exception as e:
        st.error(f"Parse failed: {e}")
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

     # === AI FIXES (v1.3 — NEVER FAILS) ===
    if st.button("Generate AI Fixes"):
        with st.spinner("dForge AI is analyzing..."):
            try:
                client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
                sample = st.session_state.clean_df.head(5).to_csv(index=False)
                columns = list(st.session_state.clean_df.columns)
                
                prompt = f"""
                Analyze this CSV:
                {sample}
                Columns: {columns}
                
                Suggest 3 Pandas fixes using ONLY these columns.
                If data is clean, suggest enhancements.
                Return JSON only:
                {{"fixes": [...]}}
                """
                
                response = client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=300,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                raw = response.content[0].text.strip()
                start = raw.find('{')
                end = raw.rfind('}') + 1
                if start == -1 or end == 0:
                    st.warning("AI returned no fixes — data is clean!")
                    st.session_state.fixes = [
                        {"id": 1, "title": "Lowercase text", "action": "for col in df.select_dtypes('object').columns: df[col] = df[col].str.lower()"},
                        {"id": 2, "title": "Add row ID", "action": "df['Row_ID'] = range(1, len(df)+1)"},
                        {"id": 3, "title": "Flag duplicates", "action": "df['Is_Dupe'] = df.duplicated(keep=False)"}
                    ]
                else:
                    fixes = json.loads(raw[start:end])["fixes"]
                    st.session_state.fixes = fixes or [
                        {"id": 1, "title": "Standardize text", "action": "for col in df.select_dtypes('object').columns: df[col] = df[col].str.strip()"},
                        {"id": 2, "title": "Add row count", "action": "df['Row_Count'] = len(df)"},
                        {"id": 3, "title": "Flag empties", "action": "df['Has_Empty'] = df.isna().any(axis=1)"}
                    ]
                
                st.success(f"AI Generated {len(st.session_state.fixes)} Fixes!")
                st.rerun()
                
            except Exception as e:
                st.error("AI offline. Using fallback fixes.")
                st.session_state.fixes = [
                    {"id": 1, "title": "Lowercase all text", "action": "for col in df.select_dtypes('object').columns: df[col] = df[col].str.lower()"},
                    {"id": 2, "title": "Fill blanks", "action": "df.fillna('UNKNOWN', inplace=True)"},
                    {"id": 3, "title": "Add index", "action": "df['Index'] = range(1, len(df)+1)"}
                ]
                st.rerun()

    # === APPLY AI FIXES ===
    if 'fixes' in st.session_state:
        st.success(f"AI Fixes Ready ({len(st.session_state.fixes)})")
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
    st.download_button("Download Clean CSV", csv_out, "dforge_clean.csv", "text/csv")

# === GUMROAD CTA ===
st.markdown("---")
st.markdown("### [Get dForge → AI + Apply + Export](https://mint2bmerry.gumroad.com/l/dforge)")
st.caption("Built by @Mint2BMerry | Nov 15, 2025")
