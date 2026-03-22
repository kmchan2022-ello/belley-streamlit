import streamlit as st
from core.db import init_db

st.set_page_config(page_title="Foresight Protocol", layout="wide")


def main():
    init_db()
    st.sidebar.title("Foresight Protocol")
    st.sidebar.markdown("Internal prediction markets for strategy.")
    st.write("Use the sidebar Pages menu to navigate between Markets, Market Detail, Create Market, Admin Resolve, and Leaderboard.")


if __name__ == "__main__":
    main()
