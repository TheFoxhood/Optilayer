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
            # Replace with Claude API (get key from anthropic.com)
            import anthropic
            client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
            
            prompt = f"""
            Analyze this Notion CSV:
            {df.head(10).to_csv(index=False)}
            
            Suggest 3 actionable fixes. Return JSON:
            {{
                "fixes": [
                    {{"id": 1, "title": "Merge columns", "action": "df['Full Name'] = df['First'] + ' ' + df['Last']"}},
                    ...
                ]
            }}
            """
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            import json
            fixes = json.loads(response.content[0].text)["fixes"]
            
            for fix in fixes:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"• {fix['title']}")
                with col2:
                    if st.button("Apply", key=fix["id"]):
                        exec(fix["action"])
                        st.success("Applied!")
                        st.rerun()
