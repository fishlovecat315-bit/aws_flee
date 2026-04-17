from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class RawCostRecord(Base):
    __tablename__ = "raw_cost_records"
    __table_args__ = (
        UniqueConstraint("account_id", "date", "service", "tag_key", "tag_value"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    account_id: Mapped[str] = mapped_column(String(20), nullable=False)
    account_name: Mapped[str] = mapped_column(String(50), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    service: Mapped[str] = mapped_column(String(100), nullable=False)
    tag_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tag_value: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    amount_usd: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD", server_default="USD")
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="NOW()"
    )


class AllocationRule(Base):
    __tablename__ = "allocation_rules"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    account_name: Mapped[str] = mapped_column(String(50), nullable=False)
    tag_value: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    rule_type: Mapped[str] = mapped_column(String(20), nullable=False)
    business_module: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ratios: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    special_config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="TRUE")
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default="NOW()")
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default="NOW()")


class AllocatedCostRecord(Base):
    __tablename__ = "allocated_cost_records"
    __table_args__ = (
        Index("idx_allocated_date", "date"),
        Index("idx_allocated_dept", "department"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    account_name: Mapped[str] = mapped_column(String(50), nullable=False)
    tag_value: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    business_module: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    department: Mapped[str] = mapped_column(String(50), nullable=False)
    amount_usd: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    rule_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True
    )
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="NOW()"
    )


class AllocationRuleHistory(Base):
    __tablename__ = "allocation_rule_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    rule_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    changed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default="NOW()")
    old_value: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    changed_by: Mapped[str] = mapped_column(
        String(100), default="admin", server_default="'admin'"
    )


class AlertThreshold(Base):
    __tablename__ = "alert_thresholds"
    __table_args__ = (UniqueConstraint("department"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    department: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    monthly_threshold_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="TRUE")
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default="NOW()")


class AwsCredentialSetting(Base):
    """存储 AWS 凭证和账号配置，key-value 形式，每个 key 唯一。"""
    __tablename__ = "aws_credential_settings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default="NOW()")


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    accounts_synced: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    records_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
