import streamlit as st
import pandas as pd

st.title("OptiLayer v0.4 - Notion DB Cleaner")

uploaded_file = st.file_uploader("Upload CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.write("### Original Data")
    st.dataframe(df)

    # === METRICS ===
    total = len(df)
    dupes = df.duplicated().sum()
    dupe_rate = dupes / total if total > 0 else 0
    st.metric("Dupe Rate", f"{dupe_rate:.1%}", f"{dupes} duplicate rows")

    # === 1-CLICK DEDUPE ===
    if st.button("🧹 Deduplicate Now"):
        clean_df = df.drop_duplicates()
        st.success(f"Cleaned! {len(df) - len(clean_df)} rows removed.")
        st.dataframe(clean_df)

        # === DOWNLOAD CLEAN CSV ===
        csv = clean_df.to_csv(index=False).encode()
        st.download_button(
            label="⬇️ Download Clean CSV",
            data=csv,
            file_name="clean_notion_db.csv",
            mime="text/csv"
        )

        # === REAL AI + 1-CLICK APPLY (v0.4) ===
    if st.button("Generate AI Fixes"):
        with st.spinner("Analyzing with AI..."):
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
                
                sample_csv = df.head(5).to_csv(index=False)
                
                prompt = f"""
                Analyze this Notion CSV schema and data:
                {sample_csv}
                
                Suggest 3 actionable Pandas code fixes for optimization (e.g., merge columns, fill empties, parse dates).
                Return JSON only, no extra text or explanations:
                {{
                    "fixes": [
                        {{"id": 1, "title": "Merge Name columns", "action": "df['Full Name'] = df['First Name'].fillna('') + ' ' + df['Last Name'].fillna('')"}},
                        {{"id": 2, "title": "Fill missing emails", "action": "df['Email'].fillna('unknown@example.com', inplace=True)"}},
                        {{"id": 3, "title": "Parse dates", "action": "df['Date'] = pd.to_datetime(df['Date'], errors='coerce')"}}
                    ]
                }}
                """
                
                response = client.messages.create(
                    model="claude-3-haiku-20240307",  # ← FIXED: No -v1:0
                    max_tokens=400,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                import json
                ai_output = response.content[0].text.strip()
                # Robust JSON extraction (handles minor LLM fluff)
                start = ai_output.find('{')
                end = ai_output.rfind('}') + 1
                if start != -1 and end != 0:
                    fixes_json = ai_output[start:end]
                    fixes = json.loads(fixes_json).get("fixes", [])
                else:
                    fixes = []  # Fallback if parse fails
                
                if fixes:
                    st.success("AI Fixes Generated!")
                    for fix in fixes:
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.write(f"• {fix['title']}")
                        with col2:
                            if st.button("Apply", key=f"apply_{fix['id']}"):
                                try:
                                    exec(fix["action"])
                                    st.success(f"Applied: {fix['title']}")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Apply failed: {e}")
                else:
                    st.warning("No fixes suggested—data looks clean!")
                    
            except Exception as e:
                st.error(f"AI error: {e}. Check model/key/network.")
