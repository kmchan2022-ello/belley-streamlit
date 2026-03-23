import streamlit as st
from core.db import get_session, User

st.title("👥 Centralized Approvers (Cross-Department)")

# Toggle approvers (Marketing, Finance, Legal, Data, Product = 5 total)
users = session.query(User).all()
for user in users:
    col1, col2 = st.columns([3,1])
    with col1: st.write(f"{user.name} ({user.email})")
    with col2:
        if st.button(f"{'✅' if user.is_approver else '➕'} {user.name}", key=f"toggle_{user.id}"):
            user.is_approver = not user.is_approver
            session.commit()
            st.rerun()
