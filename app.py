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
            
            # Sample CSV for prompt (first 5 rows)
            sample_csv = df.head(5).to_csv(index=False)
            
            prompt = f"""
            Analyze this Notion CSV schema and data:
            {sample_csv}
            
            Suggest 3 actionable Pandas code fixes for optimization (e.g., merge columns, fill empties).
            Return JSON only:
            {{
                "fixes": [
                    {{"id": 1, "title": "Fix suggestion 1", "action": "df['NewCol'] = df['Col1'] + ' ' + df['Col2']"}},
                    {{"id": 2, "title": "Fix suggestion 2", "action": "df['Email'].fillna('unknown@example.com', inplace=True)"}},
                    {{"id": 3, "title": "Fix suggestion 3", "action": "df['Date'] = pd.to_datetime(df['Date'])"}},
                    ...
                ]
            }}
            """
            
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",  # Or haiku for speed
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}]
            )
            
            import json
            ai_output = json.loads(response.content[0].text)
            fixes = ai_output.get("fixes", [])
            
            if fixes:
                st.success("AI Fixes Generated!")
                for fix in fixes:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write(f"• {fix['title']}")
                    with col2:
                        if st.button("Apply", key=f"apply_{fix['id']}"):
                            try:
                                exec(fix['action'])
                                st.success(f"Applied: {fix['title']}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Apply failed: {e}")
            else:
                st.warning("No fixes suggested—data looks clean!")
                
        except KeyError:
            st.error("API key not found. Check .streamlit/secrets.toml")
        except Exception as e:
            st.error(f"AI error: {e}. Check key or network.")
