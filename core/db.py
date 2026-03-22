from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

engine = create_engine("sqlite:///foresight.db", echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)           # Public username
    email = Column(String, unique=True)          # ← ADD THIS LINE  
    role = Column(String)
    position = Column(String)                    # ← ADD IF MISSING
    token_balance = Column(Float, default=1000.0)
    credibility_score = Column(Float, default=1.0)


class Market(Base):
    __tablename__ = "markets"
    id = Column(Integer, primary_key=True)
    module = Column(String)          # Targets / PMF / M&A
    question = Column(Text)
    status = Column(String, default="open")
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    current_p_yes = Column(Float, default=0.5)
    liquidity_param = Column(Float, default=0.05)
    trigger_threshold = Column(Float, default=0.45)
    creator_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    q_yes = Column(Float, default=0.0)
    q_no = Column(Float, default=0.0)
    oracle_source = Column(Text)
    metric_definition = Column(Text)
    edge_cases = Column(Text)


class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True)
    market_id = Column(Integer, ForeignKey("markets.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    side = Column(String)           # "YES" or "NO"
    stake = Column(Float)
    p_before = Column(Float)
    p_after = Column(Float)
    rationale = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    market_id = Column(Integer, ForeignKey("markets.id"))
    type = Column(String)           # trigger_fired / resolved / created
    payload = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()

