"""Bank Statement Intelligence API endpoints for M16"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.dependencies import get_current_user, get_current_tenant
from app.models import User, Tenant
from app.models.bsi import StatementStatus, TransactionCategory, TransactionType
from app.services.bsi_service import BSIService
from app.schemas.bsi import (
    BankStatementCreate, BankStatementUpdate, BankStatementResponse,
    BankTransactionUpdate, BankTransactionResponse,
    TransactionRuleCreate, TransactionRuleUpdate, TransactionRuleResponse,
    BSIReportResponse, BSIAnalysisSummary
)

router = APIRouter(prefix="/bsi", tags=["Bank Statement Intelligence"])


# Bank Statements
@router.post("/statements", response_model=BankStatementResponse)
def create_statement(
    data: BankStatementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Create a bank statement for processing"""
    service = BSIService(db)
    return service.create_statement(tenant.id, current_user.id, data.document_id)


@router.get("/statements", response_model=List[BankStatementResponse])
def get_statements(
    status: Optional[StatementStatus] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Get all bank statements"""
    service = BSIService(db)
    statements, _ = service.get_statements(tenant.id, skip, limit, status)
    return statements


@router.get("/statements/{statement_id}", response_model=BankStatementResponse)
def get_statement(
    statement_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a bank statement by ID"""
    service = BSIService(db)
    statement = service.get_statement(statement_id)
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")
    return statement


@router.put("/statements/{statement_id}", response_model=BankStatementResponse)
def update_statement(
    statement_id: str,
    data: BankStatementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update bank statement details"""
    service = BSIService(db)
    statement = service.update_statement(statement_id, data)
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")
    return statement


@router.post("/statements/{statement_id}/verify", response_model=BankStatementResponse)
def verify_statement(
    statement_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Verify a bank statement"""
    service = BSIService(db)
    statement = service.verify_statement(statement_id, current_user.id)
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")
    return statement


# Transactions
@router.get("/statements/{statement_id}/transactions", response_model=List[BankTransactionResponse])
def get_transactions(
    statement_id: str,
    category: Optional[TransactionCategory] = None,
    transaction_type: Optional[TransactionType] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get transactions for a statement"""
    service = BSIService(db)
    transactions, _ = service.get_transactions(
        statement_id, skip, limit, category, transaction_type
    )
    return transactions


@router.put("/transactions/{transaction_id}", response_model=BankTransactionResponse)
def update_transaction(
    transaction_id: str,
    data: BankTransactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a transaction"""
    service = BSIService(db)
    transaction = service.update_transaction(transaction_id, data)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


@router.post("/transactions/{transaction_id}/categorize", response_model=BankTransactionResponse)
def categorize_transaction(
    transaction_id: str,
    category: TransactionCategory,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually categorize a transaction"""
    service = BSIService(db)
    transaction = service.categorize_transaction(transaction_id, category, True)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


# Rules
@router.get("/rules", response_model=List[TransactionRuleResponse])
def get_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Get categorization rules"""
    service = BSIService(db)
    return service.get_rules(tenant.id)


@router.post("/rules", response_model=TransactionRuleResponse)
def create_rule(
    data: TransactionRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Create a categorization rule"""
    service = BSIService(db)
    return service.create_rule(tenant.id, current_user.id, data)


# Analysis
@router.get("/statements/{statement_id}/analysis", response_model=BSIAnalysisSummary)
def get_analysis(
    statement_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get analysis summary for a statement"""
    service = BSIService(db)
    analysis = service.get_analysis_summary(statement_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Statement not found")
    return analysis


@router.post("/statements/{statement_id}/report", response_model=BSIReportResponse)
def generate_report(
    statement_id: str,
    report_type: str = Query("summary", description="Report type: summary, detailed, trends"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Generate an analysis report"""
    service = BSIService(db)
    return service.generate_report(tenant.id, statement_id, current_user.id, report_type)
