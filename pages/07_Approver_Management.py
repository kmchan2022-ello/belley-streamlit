import streamlit as st
from core.db import get_session, User

st.title("Approver Management")

session = get_session()
users = session.query(User).all()

for user in users:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(f"{user.name} ({user.email})")
    with col2:
        label = "✅ Approver" if user.is_approver else "➕ Make approver"
        if st.button(label, key=f"toggle_{user.id}"):
            user.is_approver = 0 if user.is_approver else 1
            session.commit()
            st.rerun()

session.close()

