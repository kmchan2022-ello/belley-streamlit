import streamlit as st
from core.db import get_session, Market, User, Trade
from core.settlement import resolve_market

st.title("Admin: Market Approval & Resolve")

# Fetch markets (exclude deleted)
session = get_session()
markets = session.query(Market).filter(Market.status != "deleted").all()
session.close()

if not markets:
    st.info("No markets available.")
else:
    status_priority = {
        "pending": 0,
        "open": 1,
        "live": 1,
        "flagged": 2,
        "under_review": 3,
        "requires_edits": 4,
        "resolved": 99,
    }

    def sort_key(m):
        return (
            status_priority.get(m.status, 999),
            getattr(m, "start_time", None) or m.id,
        )

    markets_sorted = sorted(markets, key=sort_key)

    market_options = {
        f"{m.id} | {m.status} | {m.question[:50]}...": m.id
        for m in markets_sorted
    }

    selected_label = st.selectbox("Market", options=list(market_options.keys()))
    market_id = market_options[selected_label]

    # Fetch selected market + creator + trades
    session = get_session()
    m = session.get(Market, market_id)

    creator = None
    creator_id = getattr(m, "creator_id", None)
    if creator_id:
        creator = session.get(User, creator_id)

    trades = session.query(Trade).filter_by(market_id=market_id).all()
    session.close()

    # Header
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Status", m.status if m else "N/A")
    with col2:
        st.metric("Creator", creator.name if creator else "Unknown")
    with col3:
        st.metric(
            "End",
            m.end_time.strftime("%b %d") if m and m.end_time else "N/A",
        )

    st.markdown("---")

    if not m:
        st.error("Market not found!")

    else:
        # PENDING
        if m.status == "pending":
            st.info("🚀 Optimistic approval")

            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("✅ Mark Live"):
                    session = get_session()
                    target = session.get(Market, market_id)
                    target.status = "open"
                    session.commit()
                    session.close()
                    st.rerun()

            with col2:
                if st.button("🚩 Flag"):
                    session = get_session()
                    target = session.get(Market, market_id)
                    target.status = "flagged"
                    session.commit()
                    session.close()
                    st.rerun()

            with col3:
                if st.button("❌ Delete"):
                    session = get_session()
                    target = session.get(Market, market_id)
                    target.status = "deleted"
                    session.commit()
                    session.close()
                    st.rerun()

        # FLAGGED
        elif m.status == "flagged":
            st.warning("🚩 FLAGGED - Committee review")
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("✅ Approve"):
                    session = get_session()
                    target = session.get(Market, market_id)
                    target.status = "open"
                    session.commit()
                    session.close()
                    st.rerun()

            with col2:
                if st.button("❌ Reject"):
                    session = get_session()
                    target = session.get(Market, market_id)
                    target.status = "deleted"
                    session.commit()
                    session.close()
                    st.rerun()

            with col3:
                if st.button("✏️ Edits"):
                    session = get_session()
                    target = session.get(Market, market_id)
                    target.status = "requires_edits"
                    session.commit()
                    session.close()
                    st.rerun()

        # LIVE → RESOLVE (centralized + Phase 2 oracle fetch)
        elif m.status in ["open", "live"]:
            st.success("✅ Centralized Resolution - Verify Data Accuracy")

            # Core market info
            st.write("**Market Question:**", m.question)
            st.write("**Volume:**", f"${sum(t.stake for t in trades):,.0f}")
            st.write("**Final P(YES):**", f"{getattr(m, 'current_p_yes', 0.5):.1%}")

            # Oracle details
            st.markdown("### 🔎 Oracle & Metric")
            if m.oracle_source:
                st.markdown(f"**[Oracle URL]({m.oracle_source})**")
            else:
                st.write("_No oracle URL provided_")
            st.write("**Metric definition & edge cases:**")
            st.write(m.metric_definition or "_Not provided_")

            # 🤖 Phase 2: Semi-automatic oracle fetch
            st.markdown("### 🤖 Auto-fetch Oracle Outcome")
            if "oracle_suggestion" not in st.session_state:
                st.session_state.oracle_suggestion = None
                st.session_state.oracle_explanation = ""

            if st.button("🔍 Fetch Suggested Outcome"):
                try:
                    from core.oracle import fetch_oracle_outcome

                    outcome, explanation = fetch_oracle_outcome(
                        m.oracle_source or "",
                        m.metric_definition or "",
                    )
                    if outcome is not None:
                        st.session_state.oracle_suggestion = outcome
                        st.session_state.oracle_explanation = explanation
                        st.success(f"Suggested outcome: **{'YES' if outcome else 'NO'}**")
                        st.info(explanation)
                    else:
                        st.session_state.oracle_suggestion = None
                        st.session_state.oracle_explanation = explanation
                        st.warning("❌ Could not auto-fetch oracle outcome")
                        st.info(explanation)
                except Exception as e:
                    st.warning("❌ Error running oracle fetch")
                    st.error(str(e))

            if st.session_state.oracle_suggestion is not None:
                st.info(
                    f"🤖 Oracle suggestion: **{'YES' if st.session_state.oracle_suggestion else 'NO'}**"
                )
                if st.session_state.oracle_explanation:
                    st.caption(st.session_state.oracle_explanation)

            st.info("Approver must verify the oracle outcome before resolving.")

            outcome = st.radio("Final outcome (after checking oracle)", ["YES", "NO"])
            data_check = st.text_area("Resolution notes (what you saw in the oracle)")

            if st.button("🔚 Resolve Market"):
                resolve_market(
                    market_id,
                    outcome_yes=(outcome == "YES"),
                    rationale=data_check,
                )
                st.success("✅ Resolved by centralized approver")
                st.rerun()

        # RESOLVED
        elif m.status == "resolved":
            st.info("🏁 RESOLVED")

            if st.button("🗑️ Delete Resolved Market"):
                session = get_session()
                target = session.get(Market, market_id)
                target.status = "deleted"
                session.commit()
                session.close()
                st.success("Market deleted successfully.")
                st.rerun()

        # OTHER STATES
        else:
            st.warning(f"📋 {m.status}")
            if st.button("Force Open"):
                session = get_session()
                target = session.get(Market, market_id)
                target.status = "open"
                session.commit()
                session.close()
                st.rerun()
