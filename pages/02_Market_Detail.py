#what this page does: Loads a market, shows its live probability, charts its history, 
#lets you trade, and displays trade rationales. 
#It’s the live trading dashboard that execs would watch daily
# core/pricing.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from core.db import get_session, Market, Trade, User, Event
from sqlalchemy import func

st.title("Market Detail")

# 1. Load markets (hide deleted)
session = get_session()
markets = session.query(Market).filter(Market.status != "deleted").all()
session.close()

if not markets:
    st.info("No markets yet. Create one first.")
    st.stop()

market_ids = [m.id for m in markets]
market_id = st.selectbox("Select market", options=market_ids)

# 2. Load market details
session = get_session()
m = session.query(Market).get(market_id)
trades = session.query(Trade).filter_by(market_id=market_id).order_by(Trade.timestamp).all()
events = session.query(Event).filter_by(market_id=market_id).all()
users = session.query(User).all()
session.close()

if not m:
    st.error("Market not found.")
    st.stop()

# 3. **SAFE PRICE DISPLAY** - No imports needed!
def safe_price_display(market):
    """Safe price calculation - works with ANY pricing.py version"""
    # Just use the DB value directly - safest approach
    return getattr(market, 'current_p_yes', 0.5)

p_yes = safe_price_display(m)

# Market header
st.subheader(m.question)
col1, col2 = st.columns(2)
col1.metric("P(YES)", f"{p_yes:.1%}")
col2.metric("Status", m.status)

# 4. Fast movement check
trading_enabled = True
if m.status == "open" and len(trades) >= 3:
    try:
        recent = trades[-10:]
        df = pd.DataFrame([
            {"time": t.timestamp, "p": getattr(t, 'p_after', 0.5)} for t in recent
        ])
        if len(df) > 1:
            df["time_diff"] = df["time"].diff().dt.total_seconds().fillna(60)
            df["p_change"] = df["p"].diff().abs().fillna(0)
            df["velocity"] = df["p_change"] / df["time_diff"].replace(0, 60)
            
            max_velocity = df["velocity"].max()
            if max_velocity > 0.05:
                st.error(f"🚨 **MARKET PAUSED** - Moving {max_velocity:.1%}/sec")
                trading_enabled = False
    except:
        pass  # Silently continue

# 5. Events & Chart
if any(e.type == "trigger_fired" for e in events):
    st.warning("⚠️ Escalation triggered")

if trades:
    try:
        df_chart = pd.DataFrame([
            {"time": t.timestamp, "P(YES)": getattr(t, 'p_after', 0.5)} 
            for t in trades
        ]).set_index("time").sort_index()
        st.line_chart(df_chart["P(YES)"], use_container_width=True)
    except:
        st.info("Chart unavailable")

# 6. Trading section
st.markdown("### Place Trade")
user_map = {u.name: u.id for u in users}

if m.status != "open":
    st.warning(f"❌ Trading disabled - Market **{m.status}**")
elif not trading_enabled:
    st.warning("❌ Trading paused - probability moving too fast")
elif not user_map:
    st.info("No users available.")
else:
    user_name = st.selectbox("User", options=list(user_map.keys()))
    side = st.radio("Side", ["YES", "NO"], horizontal=True)
    stake = st.slider("Stake", 10.0, 200.0, 50.0)
    rationale = st.text_area("Rationale", height=80)
    
    if st.button("Submit Trade", type="primary"):
        try:
            from core.pricing import place_trade  # ONLY import place_trade
            result = place_trade(market_id, user_map[user_name], side, stake, rationale)
            st.success("✅ Trade placed!")
            st.rerun()
        except Exception as e:
            st.error(f"❌ {str(e)}")

# 7. Recent Activity
st.markdown("### Recent Activity")
if trades:
    for t in trades[-10:][::-1]:
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            st.write(f"**{getattr(t, 'side', 'N/A')}**")
        with col2:
            st.write(f"${getattr(t, 'stake', 0):.0f}")
        with col3:
            st.caption(getattr(t, 'rationale', '')[:100] + "...")

if m.status == "resolved" and st.button("⚖️ Dispute This Resolution"):
    session = get_session()
    target = session.get(Market, market_id)  # fetch fresh from new session
    target.status = "disputed"
    session.commit()
    session.close()
    st.rerun()

