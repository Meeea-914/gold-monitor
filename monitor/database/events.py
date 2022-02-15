from monitor.database import GoldEvent
from sqlalchemy import Boolean, Column, DateTime, Integer, String


class HarvesterPlotsEvent(GoldEvent):
    __tablename__ = "harvester_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime, index=True, nullable=False)
    host = Column(String(255), nullable=False)
    plot_count = Column(Integer)
    portable_plot_count = Column(Integer)
    plot_size = Column(Integer)
    portable_plot_size = Column(Integer)


class ConnectionsEvent(GoldEvent):
    __tablename__ = "connection_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime, index=True, nullable=False)
    full_node_count = Column(Integer)
    farmer_count = Column(Integer)
    wallet_count = Column(Integer)
    harvester_count = Column(Integer)


class BlockchainStateEvent(GoldEvent):
    __tablename__ = "blockchain_state_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime, index=True, nullable=False)
    space = Column(String(32))
    diffculty = Column(Integer)
    peak_height = Column(String(32))
    mempool_size = Column(Integer)
    synced = Column(Boolean())


class WalletBalanceEvent(GoldEvent):
    __tablename__ = "wallet_balance_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime, index=True, nullable=False)
    confirmed = Column(String(32))
    farmed = Column(String(32))


class SignagePointEvent(GoldEvent):
    __tablename__ = "signage_point_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime, index=True, nullable=False)
    challenge_hash = Column(String(66), index=True)
    signage_point = Column(String(66), index=True)
    signage_point_index = Column(Integer)


class FarmingInfoEvent(GoldEvent):
    __tablename__ = "farming_info_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime, index=True, nullable=False)
    challenge_hash = Column(String(66), index=True)
    signage_point = Column(String(66), index=True)
    passed_filter = Column(Integer)
    proofs = Column(Integer)
    total_plots = Column(Integer)


class PoolStateEvent(GoldEvent):
    __tablename__ = "pool_state_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime, index=True, nullable=False)
    p2_singleton_puzzle_hash = Column(String(66), default="", nullable=False)
    pool_url = Column(String(255))
    current_points = Column(Integer)
    current_difficulty = Column(Integer)
    points_found_since_start = Column(Integer)
    points_acknowledged_since_start = Column(Integer)
    points_found_24h = Column(Integer)
    points_acknowledged_24h = Column(Integer)
    num_pool_errors_24h = Column(Integer)


class PriceEvent(GoldEvent):
    __tablename__ = "price_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime, index=True, nullable=False)
    usd_cents = Column(Integer)
    eur_cents = Column(Integer)
    btc_satoshi = Column(Integer)
    eth_gwei = Column(Integer)
