import streamlit as st
from core.db import get_session, User
from sqlalchemy import func

st.title("🔐 Create User")

with st.form("user_form"):
    email = st.text_input("Company Email", placeholder="ethanpark@fnce313.com")
    username = st.text_input("Username", placeholder="trade_ninja")
    role = st.selectbox("Role", ["Finance", "Product", "Ops", "CorpDev", "Sales"])
    position = st.selectbox("Position", ["Employee", "Approver"])
    
    submitted = st.form_submit_button("Create Anonymous User")

if submitted:
    if not email or not username:
        st.error("❌ Email and username required.")
        st.stop()
    
    email_clean = email.strip()
    username_clean = username.strip()
    
    if not email_clean.endswith("@fnce313.com"):
        st.error("❌ Only @fnce313.com emails allowed.")
        st.stop()
    
    session = get_session()
    try:
        # Email uniqueness (case-insensitive)
        existing_email = session.query(User).filter(
            func.lower(User.email) == func.lower(email_clean)
        ).first()
        if existing_email:
            st.error("❌ Email already registered.")
            st.stop()
        
        # Username uniqueness (case-insensitive) 
        existing_username = session.query(User).filter(
            func.lower(User.name) == func.lower(username_clean)
        ).first()
        if existing_username:
            st.error("❌ Username taken.")
            st.stop()
        
        u = User(
            name=username_clean,
            email=email_clean,
            role=role,
            position=position,
            token_balance=1000.0,
            credibility_score=1.0
        )
        session.add(u)
        session.commit()
        session.refresh(u)
        st.success(f"✅ '{u.name}' created! ID: {u.id}")
        st.balloons()
        
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
    finally:
        session.close()
