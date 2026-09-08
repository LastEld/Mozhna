from datetime import datetime, timezone
import os
from sqlalchemy import create_engine, String, Integer, Text, JSON, Float, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def timestamp():
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class Record(Base):
    __tablename__ = 'records'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(128), index=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class OwnerState(Base):
    """Durable serialization point and global login budget for one configured owner."""
    __tablename__ = 'owner_state'
    owner_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, default=0)
    login_failures: Mapped[int] = mapped_column(Integer, default=0)
    window_started: Mapped[float] = mapped_column(Float, default=0)


def lock_owner(db, owner_id):
    # A real UPDATE takes a write lock on SQLite and a row lock on PostgreSQL.
    # Acquire before reads to avoid stale snapshots and SQLite lock upgrades.
    dialect = db.get_bind().dialect.name
    if dialect == 'postgresql':
        from sqlalchemy.dialects.postgresql import insert
    elif dialect == 'sqlite':
        from sqlalchemy.dialects.sqlite import insert
    else:
        raise RuntimeError('Unsupported database dialect')
    from sqlalchemy import update
    db.execute(insert(OwnerState).values(owner_id=owner_id, revision=0,
        login_failures=0, window_started=0).on_conflict_do_nothing(index_elements=['owner_id']))
    db.execute(update(OwnerState).where(OwnerState.owner_id == owner_id)
        .values(revision=OwnerState.revision+1))
    return db.get(OwnerState, owner_id)


class LoginSession(Base):
    __tablename__ = 'sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    csrf: Mapped[str] = mapped_column(String(128))
    owner_id: Mapped[str] = mapped_column(String(128), index=True)
    expires_at: Mapped[float] = mapped_column(Float)


class Job(Base):
    __tablename__ = 'jobs'
    __table_args__ = (UniqueConstraint('owner_id', 'idempotency_key'),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(128), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    kind: Mapped[str] = mapped_column(String(40))
    provider: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40), default='queued', index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    lease_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_until: Mapped[float] = mapped_column(Float, default=0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)
    updated_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class Schedule(Base):
    __tablename__ = 'schedules'
    __table_args__ = (UniqueConstraint('owner_id', 'plan_id'),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(128), index=True)
    plan_id: Mapped[str] = mapped_column(String(64))
    interval_hours: Mapped[int] = mapped_column(Integer)
    next_due: Mapped[float] = mapped_column(Float, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)


def connect(url=None):
    url = url or os.getenv('DATABASE_URL', 'sqlite:///./mozhna.db')
    if url.startswith('postgresql://'):
        url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
    engine = create_engine(url, connect_args={'check_same_thread': False} if url.startswith('sqlite') else {}, pool_pre_ping=True)
    return engine, sessionmaker(engine, expire_on_commit=False)
