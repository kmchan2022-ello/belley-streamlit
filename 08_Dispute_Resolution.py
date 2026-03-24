import streamlit as st
from core.db import get_session, Market, DisputeHandler
from core.settlement import resolve_market

st.title("⚖️ Dispute Resolution (3/5 Random Stakers)")

# Get current user — fall back to first user in DB if session not set
current_user_id = st.session_state.get("user_id")
if not current_user_id:
    session_temp = get_session()
    from core.db import User
    first_user = session_temp.query(User).first()
    session_temp.close()
    if first_user:
        current_user_id = first_user.id
        st.session_state["user_id"] = current_user_id
    else:
        st.warning("No users found in the database.")
        st.stop()

session = get_session()
disputes = session.query(Market).filter(Market.status == "disputed").all()

for market in disputes:
    st.markdown(f"### Dispute: {market.question[:60]}...")

    handlers = session.query(DisputeHandler).filter_by(market_id=market.id).all()
    accepted = [h for h in handlers if h.status == "accepted"]
    my_handler = next((h for h in handlers if h.user_id == current_user_id), None)

    st.write(f"{len(accepted)}/5 handlers accepted")

    # --- Opt-in phase: open until 5 accepted ---
    if len(accepted) < 5 and my_handler is None:
        if st.button("🙋 Yes, I'll handle this (stake 50 tokens)", key=f"optin_{market.id}"):
            handler = DisputeHandler(
                market_id=market.id,
                user_id=current_user_id,
                stake_amount=50.0,
                status="pending"
            )
            session.add(handler)
            session.commit()
            st.success("✅ Staked! Waiting for selection...")
            st.rerun()

    # --- Voting phase: only unlocks once 5 are accepted ---
    if len(accepted) < 5:
        st.info("Waiting for 5 handlers to accept before voting opens.")
    elif my_handler and my_handler.status == "accepted" and my_handler.voted_outcome is None:
        st.info("You've been selected. Cast your vote:")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Vote YES", key=f"yes_{market.id}"):
                my_handler.voted_outcome = 1.0  # matches Float column in db
                my_handler.status = "voted"
                session.commit()
                st.rerun()
        with col2:
            if st.button("❌ Vote NO", key=f"no_{market.id}"):
                my_handler.voted_outcome = 0.0
                my_handler.status = "voted"
                session.commit()
                st.rerun()

    # --- Resolution check: first side to reach 3/5 wins ---
    if len(accepted) == 5:
        voted = [h for h in accepted if h.voted_outcome is not None]
        yes_votes = sum(1 for h in voted if h.voted_outcome == 1.0)
        no_votes  = sum(1 for h in voted if h.voted_outcome == 0.0)

        st.write(f"Votes: YES {yes_votes} / NO {no_votes} ({5 - len(voted)} pending)")

        if yes_votes >= 3:
            st.success("✅ 3/5 resolved YES")
            session.close()
            resolve_market(market.id, outcome_yes=True, rationale="3/5 dispute handlers")
            st.rerun()
        elif no_votes >= 3:
            st.success("✅ 3/5 resolved NO")
            session.close()
            resolve_market(market.id, outcome_yes=False, rationale="3/5 dispute handlers")
            st.rerun()
        elif len(voted) == 5:
            # All 5 voted but neither side reached 3 (shouldn't happen with YES/NO,
            # but catches any data integrity issues)
            st.error("⚠️ No majority reached — escalating to admin")
            market.status = "requires_admin_review"
            session.commit()

session.close()