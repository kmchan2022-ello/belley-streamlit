import streamlit as st
from core.db import get_session, Market, User
from core.settlement import resolve_market

st.title("Admin: Market Approval & Resolve")

# Fetch markets (exclude deleted)
session = get_session()
markets = session.query(Market).filter(Market.status != "deleted").all()
session.close()

if not markets:
    st.info("No markets available.")
else:
    # Priority sorting
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

    # Fetch selected market
    session = get_session()
    m = session.get(Market, market_id)

    creator = None
    creator_id = getattr(m, "creator_id", None)

    if creator_id:
        creator = session.get(User, creator_id)

    session.close()

    # Display
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
        # =========================
        # PENDING
        # =========================
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

        # =========================
        # FLAGGED
        # =========================
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

        # =========================
        # LIVE → RESOLVE
        # =========================
        elif m.status in ["open", "live"]:
            st.success("✅ LIVE - Resolve")

            outcome = st.radio("Outcome", ["YES", "NO"])
            rationale = st.text_area("Resolution notes")

            if st.button("🔚 Resolve"):
                resolve_market(
                    market_id,
                    outcome_yes=(outcome == "YES"),
                    rationale=rationale,
                )
                st.rerun()

        # =========================
        # RESOLVED → NEW DELETE FEATURE
        # =========================
        elif m.status == "resolved":
            st.info("🏁 RESOLVED")

            if st.button("🗑️ Delete Resolved Market"):
                session = get_session()
                target = session.get(Market, market_id)
                target.status = "deleted"   # soft delete
                session.commit()
                session.close()
                st.success("Market deleted successfully.")
                st.rerun()

        # =========================
        # OTHER STATES
        # =========================
        else:
            st.warning(f"📋 {m.status}")

            if st.button("Force Open"):
                session = get_session()
                target = session.get(Market, market_id)
                target.status = "open"
                session.commit()
                session.close()
                st.rerun()