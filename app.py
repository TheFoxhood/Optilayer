import streamlit as st
import pandas as pd
import json

st.title("OptiLayer v0.4 - Notion DB Cleaner")

# === FILE UPLOAD (CSV + XLSX) ===
uploaded_file = st.file_uploader("Upload CSV or XLSX", type=["csv", "xlsx"])

if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    # Initialize session state
    if 'clean_df' not in st.session_state:
        st.session_state.clean_df = df.copy()
    df = st.session_state.clean_df  # Always use live state

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

    # === AI FIXES ===
    if st.button("Generate AI Fixes"):
        with st.spinner("Analyzing..."):
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
                sample = df.head(5).to_csv(index=False)
                prompt = f"Analyze:\n{sample}\nSuggest 3 Pandas fixes. JSON only."
                response = client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=300,
                    messages=[{"role": "user", "content": prompt}]
                )
                fixes = json.loads(response.content[0].text.strip())["fixes"]
                
                st.session_state.fixes = fixes
                st.rerun()
            except Exception as e:
                st.error(f"AI error: {e}")

    # === APPLY FIXES ===
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
                        st.success("Applied!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed: {e}")

    # === LIVE PREVIEW ===
    st.write("### Live Clean Data")
    st.dataframe(st.session_state.clean_df)

    # === DOWNLOAD ===
    csv = st.session_state.clean_df.to_csv(index=False).encode()
    st.download_button("Download Clean CSV", csv, "clean_notion_db.csv", "text/csv")
