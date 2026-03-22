from datetime import datetime, timedelta
from sqlalchemy import func
from .db import get_session, Market, Trade, Event, User

def resolve_market(market_id, outcome_yes: bool, admin_id: int = None, rationale: str = None): 
    session = get_session()
    m = session.query(Market).get(market_id)
    if m is None:
        session.close()
        return
    if m.status != "open":
        session.close()
        return
    
    # **PROGRESSIVE TIME DECAY**: Calculate time window
    start = m.start_time
    end = m.end_time or datetime.utcnow()
    total_window = (end - start).total_seconds() or 1.0
    
    # **PAYOUT LIMITS**
    MAX_PROFIT_MULTIPLIER = 2.0      # Max 2x stake profit per trade
    MIN_TIME_WINDOW_HOURS = 24       # No rewards if market < 24h old
    LATE_TRADE_PENALTY = 0.2         # Trades in last 20% get 20% reward
    
    trades = session.query(Trade).filter_by(market_id=market_id).all()
    
    for t in trades:
        u = session.query(User).get(t.user_id)
        correct = (outcome_yes and t.side == "YES") or (not outcome_yes and t.side == "NO")
        
        # **NEW: Progressive time decay factor**
        time_left = max((end - t.timestamp).total_seconds(), 0.0)
        time_ratio = time_left / total_window
        
        # Progressive decay: 100% early → 20% late → 0% after end
        if time_ratio > 0.8:  # First 80% of time
            time_factor = 1.0
        elif time_ratio > 0.2:  # Last 60% of time (20-80%)
            time_factor = (time_ratio - 0.2) / 0.6  # Linear decay 20%-100%
        else:  # Last 20% - heavy penalty
            time_factor = LATE_TRADE_PENALTY
        
        # Skip if market too new
        if total_window < MIN_TIME_WINDOW_HOURS * 3600:
            time_factor = 0.0
            
        if correct:
            # Edge: how wrong market was when traded
            edge = abs((1.0 if outcome_yes else 0.0) - t.p_before)
            
            # **Base multiplier with progressive decay**
            base_mult = (0.5 + edge) * time_factor  # 0.5-1.5 × time_factor
            
            # **PAYOUT CAP 1**: Per-trade limit
            profit = min(t.stake * base_mult, t.stake * MAX_PROFIT_MULTIPLIER)
            
            # **PAYOUT CAP 2**: Minimum time requirement
            if time_factor == 0:
                profit = 0.0
            
            # **Payout**: stake back + capped profit
            u.token_balance += t.stake + profit
            
            # **Credibility**: also decays over time
            u.credibility_score += (1.0 + edge) * time_factor
            
        else:
            # Losers: flat credibility penalty (no stake returned)
            u.credibility_score -= 0.5

    # Enhanced resolution event
    m.status = "resolved"
    ev = Event(
        market_id=market_id,
        type="resolved",
        payload=f"Outcome YES={outcome_yes} | Admin ID: {admin_id} | Rationale: {rationale or 'N/A'}",
        timestamp=datetime.utcnow(),
    )
    session.add(ev)
    session.commit()
    session.close()
