import streamlit as st
import pandas as pd

st.title("OptiLayer v0.1 - Notion DB Cleaner")
uploaded_file = st.file_uploader("Upload CSV", type="csv")
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.dataframe(df.head())
    dupes = df.duplicated().sum()
    total = len(df)
    st.metric("Dupe Rate", f"{dupes / total:.1%}" if total else "0%")