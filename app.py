import streamlit as st
import pandas as pd

st.title("OptiLayer v0.2 - Notion DB Cleaner")

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
