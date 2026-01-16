"""Celery tasks for Bank Statement Intelligence processing"""
import logging
from celery import current_app as celery_app
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.bsi import BankStatement, BankTransaction, StatementStatus, TransactionCategory, TransactionType
from app.models import Document
from app.services.bsi_parser import BSIParser, ParsedStatement

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def parse_bank_statement(self, statement_id: str, tenant_id: str):
    """
    Parse a bank statement document and extract transactions.

    Args:
        statement_id: The BankStatement ID
        tenant_id: Tenant ID for isolation
    """
    db: Session = SessionLocal()

    try:
        # Get the statement
        statement = db.query(BankStatement).filter(
            BankStatement.id == statement_id,
            BankStatement.tenant_id == tenant_id
        ).first()

        if not statement:
            logger.error(f"Statement {statement_id} not found")
            return {"success": False, "error": "Statement not found"}

        # Update status to processing
        statement.status = StatementStatus.PROCESSING
        db.commit()

        # Get the document
        document = db.query(Document).filter(
            Document.id == statement.document_id
        ).first()

        if not document:
            statement.status = StatementStatus.FAILED
            statement.processing_errors = {"error": "Document not found"}
            db.commit()
            return {"success": False, "error": "Document not found"}

        # Get text content - prefer OCR text, fall back to extracted text
        text_content = document.ocr_text or document.extracted_text or ""

        if not text_content:
            statement.status = StatementStatus.FAILED
            statement.processing_errors = {"error": "No text content available"}
            db.commit()
            return {"success": False, "error": "No text content"}

        # Determine file type
        file_type = "csv" if document.mime_type == "text/csv" else "pdf"

        # Parse the statement
        parser = BSIParser()
        parsed = parser.parse_statement(text_content, file_type)

        # Update statement with parsed data
        statement.bank_name = parsed.bank_name
        statement.account_number = parsed.account_number
        statement.account_holder = parsed.account_holder
        statement.period_start = parsed.period_start
        statement.period_end = parsed.period_end
        statement.opening_balance = parsed.opening_balance
        statement.closing_balance = parsed.closing_balance
        statement.currency = parsed.currency

        # Calculate totals
        total_credits = sum(
            t.amount for t in parsed.transactions
            if t.transaction_type == "CREDIT"
        )
        total_debits = sum(
            t.amount for t in parsed.transactions
            if t.transaction_type == "DEBIT"
        )

        statement.total_credits = total_credits
        statement.total_debits = total_debits
        statement.transaction_count = len(parsed.transactions)

        # Store raw transactions
        for parsed_trans in parsed.transactions:
            # Extract counterparty
            counterparty = parser.extract_counterparty(parsed_trans.description)

            transaction = BankTransaction(
                statement_id=statement.id,
                transaction_date=parsed_trans.transaction_date,
                description=parsed_trans.description,
                amount=parsed_trans.amount,
                transaction_type=TransactionType.CREDIT if parsed_trans.transaction_type == "CREDIT" else TransactionType.DEBIT,
                running_balance=parsed_trans.balance,
                reference_number=parsed_trans.reference,
                counterparty_name=counterparty or parsed_trans.counterparty,
                category=TransactionCategory.OTHER,  # Will be categorized later
            )
            db.add(transaction)

        # Update status based on confidence
        if parsed.confidence >= 0.7:
            statement.status = StatementStatus.PROCESSED
        else:
            statement.status = StatementStatus.NEEDS_REVIEW
            statement.processing_errors = {
                "warning": f"Low confidence parsing: {parsed.confidence}",
                "fields_missing": []
            }
            if not parsed.bank_name:
                statement.processing_errors["fields_missing"].append("bank_name")
            if not parsed.account_number:
                statement.processing_errors["fields_missing"].append("account_number")

        db.commit()

        # Trigger categorization task
        categorize_transactions.delay(statement_id, tenant_id)

        logger.info(f"Parsed statement {statement_id}: {len(parsed.transactions)} transactions")

        return {
            "success": True,
            "statement_id": statement_id,
            "transactions": len(parsed.transactions),
            "confidence": parsed.confidence,
            "bank": parsed.bank_name
        }

    except Exception as e:
        logger.error(f"Error parsing statement {statement_id}: {e}")

        # Update status to failed
        try:
            statement = db.query(BankStatement).filter(
                BankStatement.id == statement_id
            ).first()
            if statement:
                statement.status = StatementStatus.FAILED
                statement.processing_errors = {"error": str(e)}
                db.commit()
        except:
            pass

        # Retry
        raise self.retry(exc=e, countdown=60)

    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2)
def categorize_transactions(self, statement_id: str, tenant_id: str):
    """
    Apply categorization rules to transactions in a statement.

    Args:
        statement_id: The BankStatement ID
        tenant_id: Tenant ID for isolation
    """
    db: Session = SessionLocal()

    try:
        from app.services.bsi_service import BSIService

        bsi_service = BSIService(db)

        # Get all rules for tenant
        rules = bsi_service.get_rules(tenant_id)

        if not rules:
            logger.info(f"No rules found for tenant {tenant_id}")
            return {"success": True, "categorized": 0}

        # Get uncategorized transactions
        transactions = db.query(BankTransaction).filter(
            BankTransaction.statement_id == statement_id,
            BankTransaction.is_category_verified == False
        ).all()

        categorized_count = 0

        for transaction in transactions:
            category = bsi_service.apply_rules_to_transaction(transaction, rules)
            if category:
                transaction.category = category
                categorized_count += 1

        db.commit()

        logger.info(f"Categorized {categorized_count}/{len(transactions)} transactions for statement {statement_id}")

        # Trigger recurring detection
        detect_recurring_transactions.delay(statement_id, tenant_id)

        return {
            "success": True,
            "categorized": categorized_count,
            "total": len(transactions)
        }

    except Exception as e:
        logger.error(f"Error categorizing transactions for {statement_id}: {e}")
        raise self.retry(exc=e, countdown=30)

    finally:
        db.close()


@celery_app.task(bind=True)
def detect_recurring_transactions(self, statement_id: str, tenant_id: str):
    """
    Detect recurring transactions in a statement.

    Looks for transactions with similar amounts and descriptions that occur regularly.

    Args:
        statement_id: The BankStatement ID
        tenant_id: Tenant ID for isolation
    """
    db: Session = SessionLocal()

    try:
        from collections import defaultdict
        from decimal import Decimal

        # Get all transactions for the statement
        transactions = db.query(BankTransaction).filter(
            BankTransaction.statement_id == statement_id
        ).order_by(BankTransaction.transaction_date).all()

        if len(transactions) < 3:
            return {"success": True, "recurring": 0}

        # Group by similar description (normalized)
        def normalize_description(desc: str) -> str:
            import re
            # Remove numbers, dates, and special chars
            normalized = re.sub(r'\d+', '', desc.lower())
            normalized = re.sub(r'[^a-z\s]', '', normalized)
            return ' '.join(normalized.split())[:50]

        groups = defaultdict(list)
        for trans in transactions:
            key = (normalize_description(trans.description), trans.transaction_type)
            groups[key].append(trans)

        recurring_count = 0

        for (desc_key, trans_type), group_transactions in groups.items():
            if len(group_transactions) >= 2:
                # Check if amounts are similar (within 10%)
                amounts = [float(t.amount) for t in group_transactions]
                avg_amount = sum(amounts) / len(amounts)

                all_similar = all(
                    abs(a - avg_amount) / avg_amount < 0.10 if avg_amount > 0 else True
                    for a in amounts
                )

                if all_similar and len(group_transactions) >= 2:
                    # Mark as recurring
                    for trans in group_transactions:
                        trans.is_recurring = True
                        recurring_count += 1

        db.commit()

        logger.info(f"Detected {recurring_count} recurring transactions for statement {statement_id}")

        return {
            "success": True,
            "recurring": recurring_count
        }

    except Exception as e:
        logger.error(f"Error detecting recurring transactions for {statement_id}: {e}")
        return {"success": False, "error": str(e)}

    finally:
        db.close()


@celery_app.task(bind=True)
def batch_process_statements(self, tenant_id: str, batch_size: int = 10):
    """
    Process all pending statements for a tenant in batch.

    Args:
        tenant_id: Tenant ID
        batch_size: Number of statements to process
    """
    db: Session = SessionLocal()

    try:
        # Get pending statements
        pending = db.query(BankStatement).filter(
            BankStatement.tenant_id == tenant_id,
            BankStatement.status == StatementStatus.PENDING
        ).limit(batch_size).all()

        if not pending:
            return {"success": True, "processed": 0}

        for statement in pending:
            parse_bank_statement.delay(statement.id, tenant_id)

        logger.info(f"Queued {len(pending)} statements for processing")

        return {
            "success": True,
            "queued": len(pending)
        }

    except Exception as e:
        logger.error(f"Error batch processing statements: {e}")
        return {"success": False, "error": str(e)}

    finally:
        db.close()
