"""Bank Statement Intelligence models for M16"""
import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Integer,
    Numeric,
    Date,
    Enum,
    Index,
    Boolean,
)
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base


class StatementStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PARSED = "parsed"
    VERIFIED = "verified"
    FAILED = "failed"


class TransactionCategory(str, enum.Enum):
    SALARY = "salary"
    RENT = "rent"
    UTILITIES = "utilities"
    GROCERIES = "groceries"
    TRANSPORTATION = "transportation"
    ENTERTAINMENT = "entertainment"
    HEALTHCARE = "healthcare"
    INSURANCE = "insurance"
    LOAN_PAYMENT = "loan_payment"
    INVESTMENT = "investment"
    TRANSFER = "transfer"
    ATM = "atm"
    POS = "pos"
    ONLINE = "online"
    CHEQUE = "cheque"
    OTHER = "other"


class TransactionType(str, enum.Enum):
    CREDIT = "credit"
    DEBIT = "debit"


class BankStatement(Base):
    """Parsed bank statements"""
    __tablename__ = "bank_statements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=False)

    # Bank details
    bank_name = Column(String(200), nullable=True)
    account_number = Column(String(50), nullable=True)  # Masked
    account_holder = Column(String(200), nullable=True)
    account_type = Column(String(50), nullable=True)  # savings, current, etc.

    # Statement period
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)

    # Summary
    opening_balance = Column(Numeric(15, 2), nullable=True)
    closing_balance = Column(Numeric(15, 2), nullable=True)
    total_credits = Column(Numeric(15, 2), nullable=True)
    total_debits = Column(Numeric(15, 2), nullable=True)
    transaction_count = Column(Integer, default=0)

    # Currency
    currency = Column(String(10), default="INR")

    # Processing status
    status = Column(Enum(StatementStatus), default=StatementStatus.PENDING)
    parsing_confidence = Column(Numeric(5, 2), nullable=True)  # RAG score 0-100

    # Parsing metadata
    parse_method = Column(String(50), nullable=True)  # ocr, pdf_extract, api
    raw_text = Column(Text, nullable=True)
    parsing_errors = Column(JSON, default=list)

    # Verification
    is_verified = Column(Boolean, default=False)
    verified_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    document = relationship("Document", foreign_keys=[document_id])
    uploader = relationship("User", foreign_keys=[uploaded_by])
    verifier = relationship("User", foreign_keys=[verified_by])
    transactions = relationship("BankTransaction", back_populates="statement", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_bank_statements_tenant_status", "tenant_id", "status"),
        Index("ix_bank_statements_document", "document_id"),
    )


class BankTransaction(Base):
    """Individual transactions from bank statements"""
    __tablename__ = "bank_transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    statement_id = Column(String(36), ForeignKey("bank_statements.id"), nullable=False)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)

    # Transaction details
    transaction_date = Column(Date, nullable=False)
    value_date = Column(Date, nullable=True)
    description = Column(Text, nullable=False)

    # Amount
    transaction_type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    balance = Column(Numeric(15, 2), nullable=True)

    # Reference
    reference_number = Column(String(100), nullable=True)
    cheque_number = Column(String(50), nullable=True)

    # Categorization
    category = Column(Enum(TransactionCategory), default=TransactionCategory.OTHER)
    category_confidence = Column(Numeric(5, 2), nullable=True)
    is_category_verified = Column(Boolean, default=False)

    # Counterparty (extracted)
    counterparty_name = Column(String(200), nullable=True)
    counterparty_account = Column(String(50), nullable=True)

    # Flags
    is_recurring = Column(Boolean, default=False)
    is_suspicious = Column(Boolean, default=False)
    suspicious_reason = Column(String(200), nullable=True)

    # Raw data
    raw_data = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    statement = relationship("BankStatement", back_populates="transactions")

    __table_args__ = (
        Index("ix_bank_transactions_statement", "statement_id"),
        Index("ix_bank_transactions_date", "transaction_date"),
        Index("ix_bank_transactions_category", "category"),
    )


class TransactionRule(Base):
    """Rules for auto-categorizing transactions"""
    __tablename__ = "transaction_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)

    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Rule conditions
    match_type = Column(String(20), nullable=False)  # contains, regex, exact
    match_field = Column(String(50), nullable=False)  # description, counterparty
    match_value = Column(String(500), nullable=False)

    # Additional conditions
    min_amount = Column(Numeric(15, 2), nullable=True)
    max_amount = Column(Numeric(15, 2), nullable=True)
    transaction_type = Column(Enum(TransactionType), nullable=True)

    # Action
    assign_category = Column(Enum(TransactionCategory), nullable=False)
    mark_as_recurring = Column(Boolean, default=False)

    # Priority (lower = higher priority)
    priority = Column(Integer, default=100)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])


class BSIReport(Base):
    """Generated BSI analysis reports"""
    __tablename__ = "bsi_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    statement_id = Column(String(36), ForeignKey("bank_statements.id"), nullable=False)
    generated_by = Column(String(36), ForeignKey("users.id"), nullable=False)

    report_type = Column(String(50), nullable=False)  # summary, detailed, trends

    # Analysis results
    analysis = Column(JSON, default=dict)
    """
    {
        "income_summary": {...},
        "expense_breakdown": {...},
        "cash_flow_analysis": {...},
        "spending_trends": [...],
        "anomalies_detected": [...],
        "monthly_comparison": {...}
    }
    """

    # Export
    file_path = Column(String(500), nullable=True)
    file_format = Column(String(20), nullable=True)  # pdf, xlsx, csv

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    statement = relationship("BankStatement", foreign_keys=[statement_id])
    generator = relationship("User", foreign_keys=[generated_by])
