# pages/05_Leaderboard.py - FINAL BULLETPROOF VERSION
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import func
from core.db import get_session, User, Trade, Market

st.title("🏆 Leaderboard - Top Credibility Scores")

view_mode = st.radio("Time Period", ["All-Time", "Current Quarter"])

session = get_session()
try:
    if view_mode == "All-Time":
        trades = session.query(
            Trade.user_id,
            User.name,
            func.sum(Trade.stake).label('total_stake'),
            func.count(Trade.id).label('trade_count'),
            func.avg(Trade.p_before).label('avg_accuracy')
        ).outerjoin(User).group_by(Trade.user_id, User.name).all()
        st.caption("📊 All trading activity")
    else:
        now = datetime.now()
        quarter_start = now.replace(month=((now.month-1)//3)*3+1, day=1)
        quarter_end = (quarter_start.replace(month=quarter_start.month%12+1) - timedelta(days=1))
        st.caption(f"Q{((now.month-1)//3)+1} {now.year}")
        
        trades = session.query(
            Trade.user_id,
            User.name,
            func.sum(Trade.stake).label('total_stake'),
            func.count(Trade.id).label('trade_count'),
            func.avg(Trade.p_before).label('avg_accuracy')
        ).outerjoin(User).filter(
            Trade.timestamp >= quarter_start,
            Trade.timestamp <= quarter_end
        ).group_by(Trade.user_id, User.name).all()

    df = pd.DataFrame(trades, columns=['user_id', 'name', 'total_stake', 'trade_count', 'avg_accuracy'])
    df['total_stake'] = pd.to_numeric(df['total_stake'], errors='coerce').fillna(0)
    df['trade_count'] = pd.to_numeric(df['trade_count'], errors='coerce').fillna(0)
    df['avg_accuracy'] = pd.to_numeric(df['avg_accuracy'], errors='coerce').fillna(0.5)
    
    df['credibility_score'] = df['total_stake'] * df['trade_count'] * (1 - df['avg_accuracy'])

    top3 = df.nlargest(3, 'credibility_score')

    if top3.empty:
        st.info("No trading activity.")
        st.stop()

    # Leaderboard display
    st.markdown("## 🥇 Top 3 Traders")
    medals = ["🥇", "🥈", "🥉"]
    for i in range(len(top3)):
        row = top3.iloc[i]
        col1, col2, col3, col4 = st.columns([1, 2, 2, 2])
        with col1:
            st.markdown(f"**{medals[i]}**")
        with col2:
            st.markdown(f"**{row['name']}**")
        with col3:
            st.metric("Score", f"{row['credibility_score']:.0f}")
        with col4:
            st.metric("Trades", f"{int(row['trade_count'])}")

    # ✅ FIXED Markets Participated - Start from TRADE records
    st.markdown("## 📊 Markets Participated")
    for i in range(len(top3)):
        row = top3.iloc[i]
        with st.expander(f"#{i+1} {row['name']} Markets", expanded=(i == 0)):
            # Start with user's trades, JOIN to markets
            user_markets = (
                session.query(
                    Market.question,
                    Trade.side,
                    Trade.stake,
                    Trade.p_before,
                    Trade.timestamp
                )
                .select_from(Trade)  # ✅ Start from Trade table
                .filter(Trade.user_id == row["user_id"])  # User's trades only
                .join(Market, Market.id == Trade.market_id)  # Join to market
                .order_by(Trade.timestamp.desc())
                .limit(10)
                .all()
            )

            if user_markets:
                df_markets = pd.DataFrame(
                    user_markets,
                    columns=["Question", "Side", "Stake", "P(Yes)", "Date"]
                )
                df_markets["Stake"] = pd.to_numeric(df_markets["Stake"], errors="coerce").fillna(0)
                st.dataframe(df_markets, use_container_width=True)
            else:
                st.info("No market data.")



    # Summary
    col1, col2, col3 = st.columns(3)
    total_traders = len(df[df['credibility_score'] > 0])
    total_trades = df['trade_count'].sum()
    top_score = top3.iloc[0]['credibility_score']

    with col1:
        st.metric("Total Traders", total_traders)
    with col2:
        st.metric("Total Trades", f"{int(total_trades)}")
    with col3:
        st.metric("Top Score", f"{top_score:.0f}")

finally:
    session.close()
