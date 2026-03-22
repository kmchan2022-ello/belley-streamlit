# core/pricing.py
# core/pricing.py - BULLETPROOF VERSION
import math
from datetime import datetime
from .db import get_session, Market, Trade, Event, User

def stable_softmax(q, b):
    """Overflow-proof LMSR prices"""
    max_q = max(q)
    exp_terms = [math.exp((qi - max_q) / b) for qi in q]
    total = sum(exp_terms)
    return [exp_term / total for exp_term in exp_terms]

def stable_lmsr_cost(q, b):
    """Overflow-proof LMSR cost"""
    max_q = max(q)
    logsumexp = max_q / b + math.log(sum(math.exp((qi - max_q) / b) for qi in q))
    return b * logsumexp

def lmsr_trade_cost(q, b, outcome_idx, shares):
    """Cost to buy `shares` of outcome"""
    q_after = q.copy()
    q_after[outcome_idx] += shares
    return stable_lmsr_cost(q_after, b) - stable_lmsr_cost(q, b)

def place_trade(market_id, user_id, side, stake, rationale):
    session = get_session()
    try:
        m = session.query(Market).get(market_id)
        u = session.query(User).get(user_id)
        
        if m.status != "open":
            raise ValueError("Market not open")
        if stake <= 0 or stake > u.token_balance:
            raise ValueError("Invalid stake")

        # Initialize shares if missing
        yes_shares = getattr(m, 'yes_shares', 100.0)
        no_shares = getattr(m, 'no_shares', 100.0)
        q = [yes_shares, no_shares]
        b = getattr(m, 'liquidity_param', 50.0)
        
        # Cap shares to prevent overflow
        SHARE_CAP = 500.0
        q = [min(qi, SHARE_CAP) for qi in q]

        # Current price before trade
        prices_before = stable_softmax(q, b)
        p_before = prices_before[0]

        # Which outcome to buy
        outcome_idx = 0 if side == "YES" else 1
        
        # Calculate actual cost
        cost = lmsr_trade_cost(q, b, outcome_idx, stake)
        
        if cost > u.token_balance:
            raise ValueError(f"Insufficient balance: need ${cost:.2f}")

        # Update shares
        if side == "YES":
            m.yes_shares = q[0] + stake
        else:
            m.no_shares = q[1] + stake

        # Update price after trade
        q_after = [getattr(m, 'yes_shares', 100.0), getattr(m, 'no_shares', 100.0)]
        prices_after = stable_softmax(q_after, b)
        p_after = prices_after[0]

        # Deduct cost from user
        u.token_balance -= cost

        # ✅ FIXED: Removed cost= parameter
        trade = Trade(
            market_id=market_id,
            user_id=user_id,
            side=side,
            stake=stake,        # shares bought
            p_before=p_before,
            p_after=p_after,
            rationale=rationale,
        )
        m.current_p_yes = p_after
        session.add(trade)

        # Trigger check
        if hasattr(m, 'trigger_threshold') and p_before >= m.trigger_threshold and p_after < m.trigger_threshold:
            ev = Event(
                market_id=market_id,
                type="trigger_fired",
                payload=f"Probability dropped below {m.trigger_threshold} at {p_after:.2f}",
                timestamp=datetime.utcnow(),
            )
            session.add(ev)

        session.commit()
        return {
            'success': True,
            'p_before': p_before,
            'p_after': p_after,
            'cost': cost  # Return cost for UI display
        }
        
    except Exception as e:
        if session:
            session.rollback()
        raise ValueError(f"Trade failed: {str(e)}")
    finally:
        session.close()
