# core/settlement.py

from datetime import datetime, timedelta
from sqlalchemy import func

from core.db import get_session, Market, Trade, Event, User, DisputeHandler


def settle_dispute_handlers(market_id, correct_outcome: bool):
    """Reward dispute handlers after a final outcome is known."""
    session = get_session()

    handlers = session.query(DisputeHandler).filter_by(
        market_id=market_id,
        status="voted"
    ).all()

    for handler in handlers:
        user = session.get(User, handler.user_id)

        if handler.voted_outcome == correct_outcome:
            # Reward: stake back + 20% bonus
            reward = handler.stake_amount * 1.2
            user.token_balance += reward
        else:
            # No penalty - just return stake
            user.token_balance += handler.stake_amount

        handler.status = "paid"

    session.commit()
    session.close()


def resolve_market(
    market_id: int,
    outcome_yes: bool,
    admin_id: int = None,
    rationale: str = None
):
    """Resolve a market, pay traders based on time-decayed edge, and mark resolved."""
    session = get_session()

    m = session.query(Market).get(market_id)
    if m is None:
        session.close()
        return
    if m.status != "open":
        session.close()
        return

    # PROGRESSIVE TIME DECAY: Calculate time window
    start = m.start_time
    end = m.end_time or datetime.utcnow()
    total_window = (end - start).total_seconds() or 1.0

    # PAYOUT LIMITS
    MAX_PROFIT_MULTIPLIER = 2.0      # Max 2x stake profit per trade
    MIN_TIME_WINDOW_HOURS = 24       # No rewards if market < 24h old
    LATE_TRADE_PENALTY = 0.2         # Trades in last 20% get 20% reward

    trades = session.query(Trade).filter_by(market_id=market_id).all()

    for t in trades:
        u = session.query(User).get(t.user_id)
        correct = (outcome_yes and t.side == "YES") or (
            not outcome_yes and t.side == "NO"
        )

        # Progressive time decay factor
        time_left = max((end - t.timestamp).total_seconds(), 0.0)
        time_ratio = time_left / total_window

        # 100% early → 20% late → 0% if market too new
        if time_ratio > 0.8:              # First 20% of time elapsed
            time_factor = 1.0
        elif time_ratio > 0.2:           # Middle 60% (20–80%)
            time_factor = (time_ratio - 0.2) / 0.6
        else:                            # Last 20% - heavy penalty
            time_factor = LATE_TRADE_PENALTY

        # Skip rewards if market too new
        if total_window < MIN_TIME_WINDOW_HOURS * 3600:
            time_factor = 0.0

        if correct:
            # Edge: how wrong market was when traded
            true_price = 1.0 if outcome_yes else 0.0
            edge = abs(true_price - t.p_before)

            # Base multiplier with progressive decay
            base_mult = (0.5 + edge) * time_factor  # 0.5–1.5 × time_factor

            # PAYOUT CAP 1: Per-trade limit
            profit = min(t.stake * base_mult, t.stake * MAX_PROFIT_MULTIPLIER)

            # PAYOUT CAP 2: Minimum time requirement
            if time_factor == 0:
                profit = 0.0

            # Payout: stake back + capped profit
            u.token_balance += t.stake + profit

            # Credibility: also decays over time
            u.credibility_score += (1.0 + edge) * time_factor

        else:
            # Losers: flat credibility penalty (no stake returned)
            u.credibility_score -= 0.5

    # Mark resolved and log event
    m.status = "resolved"
    ev = Event(
        market_id=market_id,
        type="resolved",
        payload=(
            f"Outcome YES={outcome_yes} | "
            f"Admin ID: {admin_id} | "
            f"Rationale: {rationale or 'N/A'}"
        ),
        timestamp=datetime.utcnow(),
    )
    session.add(ev)

    session.commit()
    session.close()
