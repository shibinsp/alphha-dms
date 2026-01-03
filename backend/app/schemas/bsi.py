"""Bank Statement Intelligence schemas for M16"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.models.bsi import StatementStatus, TransactionCategory, TransactionType


class BankStatementBase(BaseModel):
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    account_holder: Optional[str] = None
    account_type: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    currency: str = "INR"


class BankStatementCreate(BaseModel):
    document_id: str


class BankStatementUpdate(BaseModel):
    bank_name: Optional[str] = None
    account_holder: Optional[str] = None
    account_type: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None


class BankStatementResponse(BankStatementBase):
    id: str
    tenant_id: str
    document_id: str
    uploaded_by: str
    opening_balance: Optional[Decimal]
    closing_balance: Optional[Decimal]
    total_credits: Optional[Decimal]
    total_debits: Optional[Decimal]
    transaction_count: int
    status: StatementStatus
    parsing_confidence: Optional[Decimal]
    is_verified: bool
    verified_by: Optional[str]
    verified_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BankTransactionBase(BaseModel):
    transaction_date: date
    value_date: Optional[date] = None
    description: str
    transaction_type: TransactionType
    amount: Decimal
    balance: Optional[Decimal] = None
    reference_number: Optional[str] = None
    cheque_number: Optional[str] = None


class BankTransactionCreate(BankTransactionBase):
    statement_id: str


class BankTransactionUpdate(BaseModel):
    category: Optional[TransactionCategory] = None
    is_category_verified: Optional[bool] = None
    counterparty_name: Optional[str] = None
    is_recurring: Optional[bool] = None
    is_suspicious: Optional[bool] = None
    suspicious_reason: Optional[str] = None


class BankTransactionResponse(BankTransactionBase):
    id: str
    statement_id: str
    tenant_id: str
    category: TransactionCategory
    category_confidence: Optional[Decimal]
    is_category_verified: bool
    counterparty_name: Optional[str]
    counterparty_account: Optional[str]
    is_recurring: bool
    is_suspicious: bool
    suspicious_reason: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionRuleBase(BaseModel):
    name: str
    description: Optional[str] = None
    match_type: str  # contains, regex, exact
    match_field: str  # description, counterparty
    match_value: str
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    transaction_type: Optional[TransactionType] = None
    assign_category: TransactionCategory
    mark_as_recurring: bool = False
    priority: int = 100


class TransactionRuleCreate(TransactionRuleBase):
    pass


class TransactionRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    match_type: Optional[str] = None
    match_field: Optional[str] = None
    match_value: Optional[str] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    assign_category: Optional[TransactionCategory] = None
    mark_as_recurring: Optional[bool] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class TransactionRuleResponse(TransactionRuleBase):
    id: str
    tenant_id: str
    created_by: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BSIReportResponse(BaseModel):
    id: str
    tenant_id: str
    statement_id: str
    generated_by: str
    report_type: str
    analysis: Dict[str, Any]
    file_path: Optional[str]
    file_format: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Analysis schemas
class CategorySummary(BaseModel):
    category: str
    total_amount: Decimal
    transaction_count: int
    percentage: float


class MonthlySummary(BaseModel):
    month: str
    total_credits: Decimal
    total_debits: Decimal
    net_flow: Decimal
    transaction_count: int


class CashFlowAnalysis(BaseModel):
    opening_balance: Decimal
    closing_balance: Decimal
    total_inflow: Decimal
    total_outflow: Decimal
    net_change: Decimal
    average_daily_balance: Optional[Decimal]


class AnomalyDetection(BaseModel):
    transaction_id: str
    anomaly_type: str  # unusual_amount, unusual_timing, unusual_counterparty
    description: str
    severity: str  # low, medium, high
    transaction_date: date
    amount: Decimal


class BSIAnalysisSummary(BaseModel):
    statement_id: str
    period_start: date
    period_end: date
    cash_flow: CashFlowAnalysis
    expense_breakdown: List[CategorySummary]
    income_breakdown: List[CategorySummary]
    monthly_summary: List[MonthlySummary]
    anomalies: List[AnomalyDetection]
    recurring_transactions: List[BankTransactionResponse]
    top_counterparties: List[Dict[str, Any]]
