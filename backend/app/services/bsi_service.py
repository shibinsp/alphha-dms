"""Bank Statement Intelligence service for M16"""
import uuid
import re
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.bsi import (
    BankStatement, BankTransaction, TransactionRule, BSIReport,
    StatementStatus, TransactionCategory, TransactionType
)
from app.models import Document
from app.schemas.bsi import (
    BankStatementCreate, BankStatementUpdate,
    BankTransactionUpdate, TransactionRuleCreate, TransactionRuleUpdate,
    CategorySummary, MonthlySummary, CashFlowAnalysis,
    AnomalyDetection, BSIAnalysisSummary
)


class BSIService:
    def __init__(self, db: Session):
        self.db = db

    def create_statement(
        self,
        tenant_id: str,
        user_id: str,
        document_id: str
    ) -> BankStatement:
        """Create a bank statement record for processing"""
        statement = BankStatement(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            document_id=document_id,
            uploaded_by=user_id,
            status=StatementStatus.PENDING
        )
        self.db.add(statement)
        self.db.commit()
        self.db.refresh(statement)

        # Trigger async processing (in production, this would be a Celery task)
        # self._process_statement(statement)

        return statement

    def get_statement(self, statement_id: str) -> Optional[BankStatement]:
        """Get a bank statement by ID"""
        return self.db.query(BankStatement).filter(
            BankStatement.id == statement_id
        ).first()

    def get_statements(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 50,
        status: StatementStatus = None
    ) -> tuple[List[BankStatement], int]:
        """Get all bank statements for tenant"""
        query = self.db.query(BankStatement).filter(
            BankStatement.tenant_id == tenant_id
        )

        if status:
            query = query.filter(BankStatement.status == status)

        total = query.count()
        statements = query.order_by(
            BankStatement.created_at.desc()
        ).offset(skip).limit(limit).all()

        return statements, total

    def update_statement(
        self,
        statement_id: str,
        data: BankStatementUpdate
    ) -> Optional[BankStatement]:
        """Update bank statement details"""
        statement = self.get_statement(statement_id)
        if not statement:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(statement, field, value)

        self.db.commit()
        self.db.refresh(statement)
        return statement

    def verify_statement(
        self,
        statement_id: str,
        user_id: str
    ) -> Optional[BankStatement]:
        """Mark statement as verified"""
        statement = self.get_statement(statement_id)
        if not statement:
            return None

        statement.is_verified = True
        statement.verified_by = user_id
        statement.verified_at = datetime.utcnow()
        statement.status = StatementStatus.VERIFIED

        self.db.commit()
        self.db.refresh(statement)
        return statement

    # Transaction management
    def get_transactions(
        self,
        statement_id: str,
        skip: int = 0,
        limit: int = 100,
        category: TransactionCategory = None,
        transaction_type: TransactionType = None
    ) -> tuple[List[BankTransaction], int]:
        """Get transactions for a statement"""
        query = self.db.query(BankTransaction).filter(
            BankTransaction.statement_id == statement_id
        )

        if category:
            query = query.filter(BankTransaction.category == category)

        if transaction_type:
            query = query.filter(BankTransaction.transaction_type == transaction_type)

        total = query.count()
        transactions = query.order_by(
            BankTransaction.transaction_date.desc()
        ).offset(skip).limit(limit).all()

        return transactions, total

    def update_transaction(
        self,
        transaction_id: str,
        data: BankTransactionUpdate
    ) -> Optional[BankTransaction]:
        """Update a transaction"""
        transaction = self.db.query(BankTransaction).filter(
            BankTransaction.id == transaction_id
        ).first()

        if not transaction:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(transaction, field, value)

        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def categorize_transaction(
        self,
        transaction_id: str,
        category: TransactionCategory,
        user_verified: bool = True
    ) -> Optional[BankTransaction]:
        """Categorize a transaction"""
        transaction = self.db.query(BankTransaction).filter(
            BankTransaction.id == transaction_id
        ).first()

        if not transaction:
            return None

        transaction.category = category
        transaction.is_category_verified = user_verified

        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    # Transaction rules
    def create_rule(
        self,
        tenant_id: str,
        user_id: str,
        data: TransactionRuleCreate
    ) -> TransactionRule:
        """Create a categorization rule"""
        rule = TransactionRule(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            created_by=user_id,
            **data.model_dump()
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def get_rules(self, tenant_id: str) -> List[TransactionRule]:
        """Get all rules for tenant"""
        return self.db.query(TransactionRule).filter(
            TransactionRule.tenant_id == tenant_id,
            TransactionRule.is_active == True
        ).order_by(TransactionRule.priority).all()

    def apply_rules_to_transaction(
        self,
        transaction: BankTransaction,
        rules: List[TransactionRule]
    ) -> Optional[TransactionCategory]:
        """Apply rules to categorize a transaction"""
        for rule in rules:
            if self._rule_matches(transaction, rule):
                return rule.assign_category
        return None

    def _rule_matches(
        self,
        transaction: BankTransaction,
        rule: TransactionRule
    ) -> bool:
        """Check if a rule matches a transaction"""
        # Get the field to match
        if rule.match_field == "description":
            value = transaction.description.lower()
        elif rule.match_field == "counterparty":
            value = (transaction.counterparty_name or "").lower()
        else:
            return False

        match_value = rule.match_value.lower()

        # Check match type
        if rule.match_type == "contains":
            if match_value not in value:
                return False
        elif rule.match_type == "exact":
            if value != match_value:
                return False
        elif rule.match_type == "regex":
            if not re.search(rule.match_value, value, re.IGNORECASE):
                return False

        # Check amount conditions
        if rule.min_amount and transaction.amount < rule.min_amount:
            return False
        if rule.max_amount and transaction.amount > rule.max_amount:
            return False

        # Check transaction type
        if rule.transaction_type and transaction.transaction_type != rule.transaction_type:
            return False

        return True

    # Analysis
    def get_analysis_summary(self, statement_id: str) -> Optional[BSIAnalysisSummary]:
        """Generate analysis summary for a statement"""
        statement = self.get_statement(statement_id)
        if not statement:
            return None

        transactions, _ = self.get_transactions(statement_id, limit=10000)

        # Calculate summaries
        expense_breakdown = self._calculate_category_summary(transactions, TransactionType.DEBIT)
        income_breakdown = self._calculate_category_summary(transactions, TransactionType.CREDIT)

        # Cash flow
        cash_flow = CashFlowAnalysis(
            opening_balance=statement.opening_balance or Decimal(0),
            closing_balance=statement.closing_balance or Decimal(0),
            total_inflow=statement.total_credits or Decimal(0),
            total_outflow=statement.total_debits or Decimal(0),
            net_change=(statement.total_credits or Decimal(0)) - (statement.total_debits or Decimal(0)),
            average_daily_balance=None
        )

        # Monthly summary
        monthly_summary = self._calculate_monthly_summary(transactions)

        # Detect anomalies
        anomalies = self._detect_anomalies(transactions)

        # Find recurring transactions
        recurring = [t for t in transactions if t.is_recurring]

        # Top counterparties
        top_counterparties = self._get_top_counterparties(transactions)

        return BSIAnalysisSummary(
            statement_id=statement_id,
            period_start=statement.period_start or date.today(),
            period_end=statement.period_end or date.today(),
            cash_flow=cash_flow,
            expense_breakdown=expense_breakdown,
            income_breakdown=income_breakdown,
            monthly_summary=monthly_summary,
            anomalies=anomalies,
            recurring_transactions=recurring[:10],
            top_counterparties=top_counterparties
        )

    def _calculate_category_summary(
        self,
        transactions: List[BankTransaction],
        trans_type: TransactionType
    ) -> List[CategorySummary]:
        """Calculate category-wise summary"""
        filtered = [t for t in transactions if t.transaction_type == trans_type]
        total_amount = sum(t.amount for t in filtered) or Decimal(1)

        category_totals = {}
        for trans in filtered:
            cat = trans.category.value if trans.category else "other"
            if cat not in category_totals:
                category_totals[cat] = {"amount": Decimal(0), "count": 0}
            category_totals[cat]["amount"] += trans.amount
            category_totals[cat]["count"] += 1

        return [
            CategorySummary(
                category=cat,
                total_amount=data["amount"],
                transaction_count=data["count"],
                percentage=float(data["amount"] / total_amount * 100)
            )
            for cat, data in sorted(
                category_totals.items(),
                key=lambda x: x[1]["amount"],
                reverse=True
            )
        ]

    def _calculate_monthly_summary(
        self,
        transactions: List[BankTransaction]
    ) -> List[MonthlySummary]:
        """Calculate monthly summary"""
        monthly_data = {}

        for trans in transactions:
            month_key = trans.transaction_date.strftime("%Y-%m")
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    "credits": Decimal(0),
                    "debits": Decimal(0),
                    "count": 0
                }

            if trans.transaction_type == TransactionType.CREDIT:
                monthly_data[month_key]["credits"] += trans.amount
            else:
                monthly_data[month_key]["debits"] += trans.amount
            monthly_data[month_key]["count"] += 1

        return [
            MonthlySummary(
                month=month,
                total_credits=data["credits"],
                total_debits=data["debits"],
                net_flow=data["credits"] - data["debits"],
                transaction_count=data["count"]
            )
            for month, data in sorted(monthly_data.items())
        ]

    def _detect_anomalies(
        self,
        transactions: List[BankTransaction]
    ) -> List[AnomalyDetection]:
        """Detect anomalous transactions"""
        anomalies = []

        if not transactions:
            return anomalies

        # Calculate average amount
        amounts = [float(t.amount) for t in transactions]
        avg_amount = sum(amounts) / len(amounts)
        std_dev = (sum((a - avg_amount) ** 2 for a in amounts) / len(amounts)) ** 0.5

        # Flag transactions > 3 standard deviations
        threshold = avg_amount + (3 * std_dev)

        for trans in transactions:
            if float(trans.amount) > threshold:
                anomalies.append(AnomalyDetection(
                    transaction_id=trans.id,
                    anomaly_type="unusual_amount",
                    description=f"Amount {trans.amount} is significantly higher than average {avg_amount:.2f}",
                    severity="high",
                    transaction_date=trans.transaction_date,
                    amount=trans.amount
                ))

            if trans.is_suspicious:
                anomalies.append(AnomalyDetection(
                    transaction_id=trans.id,
                    anomaly_type="flagged_suspicious",
                    description=trans.suspicious_reason or "Flagged as suspicious",
                    severity="medium",
                    transaction_date=trans.transaction_date,
                    amount=trans.amount
                ))

        return anomalies[:20]  # Limit to 20 anomalies

    def _get_top_counterparties(
        self,
        transactions: List[BankTransaction],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top counterparties by transaction volume"""
        counterparty_totals = {}

        for trans in transactions:
            name = trans.counterparty_name or "Unknown"
            if name not in counterparty_totals:
                counterparty_totals[name] = {
                    "total_amount": Decimal(0),
                    "transaction_count": 0,
                    "credits": Decimal(0),
                    "debits": Decimal(0)
                }

            counterparty_totals[name]["total_amount"] += trans.amount
            counterparty_totals[name]["transaction_count"] += 1

            if trans.transaction_type == TransactionType.CREDIT:
                counterparty_totals[name]["credits"] += trans.amount
            else:
                counterparty_totals[name]["debits"] += trans.amount

        sorted_counterparties = sorted(
            counterparty_totals.items(),
            key=lambda x: x[1]["total_amount"],
            reverse=True
        )[:limit]

        return [
            {
                "name": name,
                "total_amount": float(data["total_amount"]),
                "transaction_count": data["transaction_count"],
                "net_flow": float(data["credits"] - data["debits"])
            }
            for name, data in sorted_counterparties
        ]

    # Report generation
    def generate_report(
        self,
        tenant_id: str,
        statement_id: str,
        user_id: str,
        report_type: str = "summary"
    ) -> BSIReport:
        """Generate an analysis report"""
        analysis = self.get_analysis_summary(statement_id)

        report = BSIReport(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            statement_id=statement_id,
            generated_by=user_id,
            report_type=report_type,
            analysis={
                "cash_flow": analysis.cash_flow.model_dump() if analysis else {},
                "expense_breakdown": [e.model_dump() for e in analysis.expense_breakdown] if analysis else [],
                "income_breakdown": [i.model_dump() for i in analysis.income_breakdown] if analysis else [],
                "monthly_summary": [m.model_dump() for m in analysis.monthly_summary] if analysis else [],
                "anomalies_count": len(analysis.anomalies) if analysis else 0
            }
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report
