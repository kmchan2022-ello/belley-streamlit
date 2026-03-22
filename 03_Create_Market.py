import streamlit as st
from datetime import datetime, timedelta
from core.db import get_session, Market, User
from sqlalchemy import func


st.title("Create Market")


username = st.text_input("Your username", help="Enter your username to check monthly limit")
module = st.selectbox("Module", ["Targets", "PMF", "M&A"])
question = st.text_area("Forecast question", height=100)
end_date = st.date_input("End date", datetime.utcnow() + timedelta(days=90))
trigger = st.slider("Trigger threshold P(YES)", 0.1, 0.9, 0.45, 0.05)
oracle = st.text_area("Oracle source / metric definition", height=80)
metric_def = st.text_area("Metric definition / edge cases", height=80)
initial_p = st.slider("Initial P(YES)", 0.1, 0.9, 0.6, 0.05)

# ✅ NEW: Liquidity parameter slider
liquidity_param = st.slider(
    "Liquidity Parameter", 
    min_value=50, 
    max_value=500, 
    value=150,
    step=25,
    help="Higher = smoother price changes per trade (less extreme swings)"
)


if st.button("Create Market", type="primary"):
    if not question.strip():
        st.error("❌ Question is required.")
    elif not username.strip():
        st.error("❌ Username is required.")
    else:
        session = get_session()
        try:
            user = session.query(User).filter_by(name=username.strip()).first()
            if not user:
                st.error("❌ Username not found. Create account first.")
            else:
                # **FIXED: CORRECT monthly limit query**
                month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                user_markets_this_month = session.query(Market).filter(
                    Market.creator_id == user.id,      # THIS USER'S markets
                    func.date(Market.created_at) >= func.date(month_start)  # This month
                ).count()


                if user_markets_this_month >= 3:
                    st.error(f"❌ **MONTHLY LIMIT REACHED**")
                    st.warning(f"You created {user_markets_this_month}/3 markets this month.")
                else:
                    m = Market(
                        module=module,
                        question=question.strip(),
                        end_time=datetime.combine(end_date, datetime.min.time()),
                        trigger_threshold=trigger,
                        oracle_source=oracle.strip(),
                        metric_definition=metric_def.strip(),
                        current_p_yes=initial_p,
                        status="pending",
                        creator_id=user.id,     # Now safe
                        created_at=datetime.utcnow(),
                        q_yes=0.0,
                        q_no=0.0,
                        liquidity_param=liquidity_param  # ✅ NEW FIELD
                    )
                    session.add(m)
                    session.commit()
                    session.refresh(m)
                    
                    remaining = 3 - user_markets_this_month - 1
                    st.success(f"✅ **MARKET CREATED** #{m.id}")
                    st.balloons()
                    st.info(f"**{remaining} markets remaining** this month")
                    st.info(f"💰 Liquidity set to {liquidity_param} (smooth pricing)")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
        finally:
            session.close()
