"""Bank Statement Parser - PDF and CSV parsing for BSI"""
import re
import csv
import io
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class ParsedTransaction:
    """Parsed transaction data"""
    transaction_date: date
    description: str
    amount: Decimal
    transaction_type: str  # CREDIT or DEBIT
    balance: Optional[Decimal] = None
    reference: Optional[str] = None
    counterparty: Optional[str] = None


@dataclass
class ParsedStatement:
    """Parsed bank statement"""
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    account_holder: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    opening_balance: Optional[Decimal] = None
    closing_balance: Optional[Decimal] = None
    currency: str = "INR"
    transactions: List[ParsedTransaction] = None
    confidence: float = 0.0
    raw_text: Optional[str] = None

    def __post_init__(self):
        if self.transactions is None:
            self.transactions = []


# Bank-specific parsing templates
BANK_TEMPLATES = {
    "HDFC": {
        "identifiers": ["HDFC BANK", "HDFC Bank Limited"],
        "date_formats": ["%d/%m/%Y", "%d-%m-%Y", "%d %b %Y"],
        "account_pattern": r"A/c\s*No[.:]?\s*(\d+)",
        "balance_pattern": r"(?:Balance|Bal)[:\s]*(?:Rs\.?|INR)?\s*([\d,]+\.?\d*)",
    },
    "ICICI": {
        "identifiers": ["ICICI BANK", "ICICI Bank Ltd"],
        "date_formats": ["%d-%m-%Y", "%d/%m/%Y"],
        "account_pattern": r"Account\s*(?:Number|No)?[:\s]*(\d+)",
        "balance_pattern": r"(?:Balance)[:\s]*(?:Rs\.?|INR)?\s*([\d,]+\.?\d*)",
    },
    "SBI": {
        "identifiers": ["STATE BANK OF INDIA", "SBI"],
        "date_formats": ["%d %b %Y", "%d-%m-%Y", "%d/%m/%Y"],
        "account_pattern": r"(?:A/c|Account)\s*(?:No)?[.:]?\s*(\d+)",
        "balance_pattern": r"(?:Balance)[:\s]*(?:Rs\.?|INR)?\s*([\d,]+\.?\d*)",
    },
    "AXIS": {
        "identifiers": ["AXIS BANK", "Axis Bank Ltd"],
        "date_formats": ["%d-%m-%Y", "%d/%m/%Y"],
        "account_pattern": r"Account\s*(?:Number|No)?[:\s]*(\d+)",
        "balance_pattern": r"(?:Balance)[:\s]*(?:Rs\.?|INR)?\s*([\d,]+\.?\d*)",
    },
    "KOTAK": {
        "identifiers": ["KOTAK MAHINDRA BANK", "Kotak"],
        "date_formats": ["%d-%m-%Y", "%d/%m/%Y", "%d-%b-%Y"],
        "account_pattern": r"A/c\s*(?:No)?[:\s]*(\d+)",
        "balance_pattern": r"(?:Balance)[:\s]*(?:Rs\.?|INR)?\s*([\d,]+\.?\d*)",
    },
}

# Transaction patterns
TRANSACTION_PATTERNS = [
    # Pattern: date description debit credit balance
    r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(.+?)\s+([\d,]+\.?\d*)\s*([\d,]+\.?\d*)?\s*([\d,]+\.?\d*)?",
    # Pattern: date reference description amount
    r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(\w+)\s+(.+?)\s+([\d,]+\.?\d*)",
    # Pattern: date description amount dr/cr
    r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(.+?)\s+([\d,]+\.?\d*)\s*(Dr|Cr|DR|CR)?",
]


class BSIParser:
    """Parser for bank statement PDFs and CSVs"""

    def __init__(self):
        self.templates = BANK_TEMPLATES

    def parse_statement(self, text: str, file_type: str = "pdf") -> ParsedStatement:
        """
        Parse a bank statement from text.
        Args:
            text: Extracted text from PDF or raw CSV content
            file_type: 'pdf' or 'csv'
        """
        if file_type == "csv":
            return self.parse_csv(text)
        return self.parse_pdf_text(text)

    def parse_pdf_text(self, text: str) -> ParsedStatement:
        """Parse bank statement from PDF text"""
        statement = ParsedStatement(raw_text=text)

        # Detect bank
        statement.bank_name = self._detect_bank(text)
        template = self.templates.get(statement.bank_name, {})

        # Extract account info
        statement.account_number = self._extract_account_number(text, template)
        statement.account_holder = self._extract_account_holder(text)

        # Extract dates
        period = self._extract_statement_period(text)
        if period:
            statement.period_start, statement.period_end = period

        # Extract balances
        balances = self._extract_balances(text, template)
        statement.opening_balance = balances.get("opening")
        statement.closing_balance = balances.get("closing")

        # Extract transactions
        statement.transactions = self._extract_transactions(text, template)

        # Calculate totals if we have transactions
        if statement.transactions:
            total_credits = sum(
                t.amount for t in statement.transactions
                if t.transaction_type == "CREDIT"
            )
            total_debits = sum(
                t.amount for t in statement.transactions
                if t.transaction_type == "DEBIT"
            )

            # Calculate confidence based on extracted data
            statement.confidence = self._calculate_confidence(statement)

        return statement

    def parse_csv(self, csv_content: str) -> ParsedStatement:
        """Parse bank statement from CSV content"""
        statement = ParsedStatement()
        transactions = []

        try:
            # Try to detect CSV dialect
            sniffer = csv.Sniffer()
            sample = csv_content[:2048]
            try:
                dialect = sniffer.sniff(sample)
            except csv.Error:
                dialect = csv.excel

            reader = csv.DictReader(io.StringIO(csv_content), dialect=dialect)

            for row in reader:
                transaction = self._parse_csv_row(row)
                if transaction:
                    transactions.append(transaction)

            statement.transactions = transactions

            # Set period from transactions
            if transactions:
                dates = [t.transaction_date for t in transactions]
                statement.period_start = min(dates)
                statement.period_end = max(dates)

            statement.confidence = 0.9 if transactions else 0.0

        except Exception as e:
            print(f"CSV parsing error: {e}")
            statement.confidence = 0.0

        return statement

    def _detect_bank(self, text: str) -> Optional[str]:
        """Detect bank from statement text"""
        text_upper = text.upper()
        for bank, template in self.templates.items():
            for identifier in template.get("identifiers", []):
                if identifier.upper() in text_upper:
                    return bank
        return None

    def _extract_account_number(self, text: str, template: dict) -> Optional[str]:
        """Extract account number from text"""
        patterns = [
            template.get("account_pattern", ""),
            r"A/c\s*(?:No)?[.:]?\s*(\d{10,20})",
            r"Account\s*(?:Number|No)?[:\s]*(\d{10,20})",
            r"(\d{10,20})",
        ]

        for pattern in patterns:
            if not pattern:
                continue
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _extract_account_holder(self, text: str) -> Optional[str]:
        """Extract account holder name"""
        patterns = [
            r"(?:Name|Account\s*Holder)[:\s]+([A-Z][A-Z\s]+)",
            r"(?:Mr\.|Mrs\.|Ms\.|M/s\.?)\s+([A-Z][A-Z\s]+)",
            r"(?:Dear|To)[,:\s]+([A-Z][A-Z\s]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Clean up name
                name = re.sub(r'\s+', ' ', name)
                if len(name) > 3 and len(name) < 100:
                    return name
        return None

    def _extract_statement_period(self, text: str) -> Optional[Tuple[date, date]]:
        """Extract statement period (start and end dates)"""
        patterns = [
            r"(?:Statement\s*)?Period[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s*(?:to|[-–])\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"From[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s*To[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"(\d{1,2}\s*\w+\s*\d{4})\s*(?:to|[-–])\s*(\d{1,2}\s*\w+\s*\d{4})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                start_str, end_str = match.groups()
                start = self._parse_date(start_str)
                end = self._parse_date(end_str)
                if start and end:
                    return (start, end)
        return None

    def _extract_balances(self, text: str, template: dict) -> Dict[str, Decimal]:
        """Extract opening and closing balances"""
        balances = {}

        # Opening balance patterns
        opening_patterns = [
            r"Opening\s*Balance[:\s]*(?:Rs\.?|INR)?\s*([\d,]+\.?\d*)",
            r"(?:Balance\s*)?B/F[:\s]*(?:Rs\.?|INR)?\s*([\d,]+\.?\d*)",
            r"(?:Previous|Start)\s*Balance[:\s]*(?:Rs\.?|INR)?\s*([\d,]+\.?\d*)",
        ]

        for pattern in opening_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                balances["opening"] = self._parse_amount(match.group(1))
                break

        # Closing balance patterns
        closing_patterns = [
            r"Closing\s*Balance[:\s]*(?:Rs\.?|INR)?\s*([\d,]+\.?\d*)",
            r"(?:Balance\s*)?C/F[:\s]*(?:Rs\.?|INR)?\s*([\d,]+\.?\d*)",
            r"(?:Final|End)\s*Balance[:\s]*(?:Rs\.?|INR)?\s*([\d,]+\.?\d*)",
            r"(?:Available|Current)\s*Balance[:\s]*(?:Rs\.?|INR)?\s*([\d,]+\.?\d*)",
        ]

        for pattern in closing_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                balances["closing"] = self._parse_amount(match.group(1))
                break

        return balances

    def _extract_transactions(self, text: str, template: dict) -> List[ParsedTransaction]:
        """Extract transactions from statement text"""
        transactions = []
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            transaction = self._parse_transaction_line(line, template)
            if transaction:
                transactions.append(transaction)

        return transactions

    def _parse_transaction_line(self, line: str, template: dict) -> Optional[ParsedTransaction]:
        """Parse a single transaction line"""
        # Try various patterns
        for pattern in TRANSACTION_PATTERNS:
            match = re.match(pattern, line)
            if match:
                groups = match.groups()
                try:
                    trans_date = self._parse_date(groups[0])
                    if not trans_date:
                        continue

                    # Determine description and amounts based on pattern
                    if len(groups) >= 4:
                        description = groups[1].strip() if len(groups) > 1 else ""
                        amount_str = groups[2] if len(groups) > 2 else "0"

                        # Check for debit/credit indicator
                        trans_type = "DEBIT"
                        if len(groups) > 3 and groups[3]:
                            indicator = groups[3].upper()
                            if indicator in ["CR", "C"]:
                                trans_type = "CREDIT"
                            elif indicator in ["DR", "D"]:
                                trans_type = "DEBIT"
                            else:
                                # Might be credit amount
                                try:
                                    credit_amount = self._parse_amount(groups[3])
                                    if credit_amount and credit_amount > 0:
                                        trans_type = "CREDIT"
                                        amount_str = groups[3]
                                except:
                                    pass

                        amount = self._parse_amount(amount_str)
                        if amount and amount > 0:
                            return ParsedTransaction(
                                transaction_date=trans_date,
                                description=description,
                                amount=amount,
                                transaction_type=trans_type,
                                balance=self._parse_amount(groups[-1]) if len(groups) > 4 else None,
                            )
                except Exception:
                    continue

        return None

    def _parse_csv_row(self, row: Dict[str, str]) -> Optional[ParsedTransaction]:
        """Parse a CSV row into a transaction"""
        # Common column name variations
        date_cols = ["date", "transaction date", "txn date", "value date", "posting date"]
        desc_cols = ["description", "narration", "particulars", "remarks", "details"]
        debit_cols = ["debit", "withdrawal", "dr", "debit amount"]
        credit_cols = ["credit", "deposit", "cr", "credit amount"]
        amount_cols = ["amount", "transaction amount", "txn amount"]
        balance_cols = ["balance", "closing balance", "available balance"]

        # Normalize keys
        row_lower = {k.lower().strip(): v for k, v in row.items()}

        # Extract date
        trans_date = None
        for col in date_cols:
            if col in row_lower and row_lower[col]:
                trans_date = self._parse_date(row_lower[col])
                if trans_date:
                    break

        if not trans_date:
            return None

        # Extract description
        description = ""
        for col in desc_cols:
            if col in row_lower and row_lower[col]:
                description = row_lower[col].strip()
                break

        # Extract amount and type
        amount = None
        trans_type = "DEBIT"

        # Check debit column
        for col in debit_cols:
            if col in row_lower and row_lower[col]:
                amount = self._parse_amount(row_lower[col])
                if amount and amount > 0:
                    trans_type = "DEBIT"
                    break

        # Check credit column
        if not amount:
            for col in credit_cols:
                if col in row_lower and row_lower[col]:
                    amount = self._parse_amount(row_lower[col])
                    if amount and amount > 0:
                        trans_type = "CREDIT"
                        break

        # Check generic amount column
        if not amount:
            for col in amount_cols:
                if col in row_lower and row_lower[col]:
                    amount = self._parse_amount(row_lower[col])
                    if amount:
                        # Negative = debit, positive = credit
                        if amount < 0:
                            amount = abs(amount)
                            trans_type = "DEBIT"
                        else:
                            trans_type = "CREDIT"
                        break

        if not amount or amount <= 0:
            return None

        # Extract balance
        balance = None
        for col in balance_cols:
            if col in row_lower and row_lower[col]:
                balance = self._parse_amount(row_lower[col])
                break

        return ParsedTransaction(
            transaction_date=trans_date,
            description=description,
            amount=amount,
            transaction_type=trans_type,
            balance=balance,
        )

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date from various formats"""
        if not date_str:
            return None

        date_str = date_str.strip()

        formats = [
            "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
            "%d/%m/%y", "%d-%m-%y",
            "%d %b %Y", "%d %B %Y",
            "%d-%b-%Y", "%d-%B-%Y",
            "%Y-%m-%d", "%Y/%m/%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        return None

    def _parse_amount(self, amount_str: str) -> Optional[Decimal]:
        """Parse amount from string"""
        if not amount_str:
            return None

        # Clean the string
        amount_str = amount_str.strip()
        amount_str = re.sub(r'[Rs.INR\s]', '', amount_str, flags=re.IGNORECASE)
        amount_str = amount_str.replace(',', '')

        # Handle negative amounts
        is_negative = False
        if amount_str.startswith('(') and amount_str.endswith(')'):
            amount_str = amount_str[1:-1]
            is_negative = True
        elif amount_str.startswith('-'):
            amount_str = amount_str[1:]
            is_negative = True

        try:
            amount = Decimal(amount_str)
            return -amount if is_negative else amount
        except (InvalidOperation, ValueError):
            return None

    def _calculate_confidence(self, statement: ParsedStatement) -> float:
        """Calculate parsing confidence score"""
        score = 0.0
        checks = 0

        # Bank detected
        checks += 1
        if statement.bank_name:
            score += 1

        # Account number
        checks += 1
        if statement.account_number:
            score += 1

        # Period dates
        checks += 1
        if statement.period_start and statement.period_end:
            score += 1

        # Balances
        checks += 1
        if statement.opening_balance or statement.closing_balance:
            score += 1

        # Transactions
        checks += 1
        if statement.transactions and len(statement.transactions) > 0:
            score += 1

        # Balance reconciliation (if we have both opening, closing, and transactions)
        if statement.opening_balance and statement.closing_balance and statement.transactions:
            total_credits = sum(t.amount for t in statement.transactions if t.transaction_type == "CREDIT")
            total_debits = sum(t.amount for t in statement.transactions if t.transaction_type == "DEBIT")
            expected_closing = statement.opening_balance + total_credits - total_debits

            checks += 1
            # Allow 1% tolerance
            tolerance = abs(statement.closing_balance) * Decimal("0.01")
            if abs(expected_closing - statement.closing_balance) <= tolerance:
                score += 1

        return round(score / checks, 2) if checks > 0 else 0.0

    def extract_counterparty(self, description: str) -> Optional[str]:
        """Extract counterparty name from transaction description"""
        # Common patterns
        patterns = [
            r"(?:TO|FROM|BY|VIA)[:\s]+([A-Z][A-Z0-9\s]+)",
            r"(?:UPI|IMPS|NEFT|RTGS)[-/]([A-Z][A-Z0-9\s]+)",
            r"(?:TRANSFER\s+(?:TO|FROM))[:\s]+([A-Z][A-Z0-9\s]+)",
            r"([A-Z][A-Z0-9\s]{3,30})(?:\s+UPI|\s+NEFT|\s+IMPS)",
        ]

        for pattern in patterns:
            match = re.search(pattern, description.upper())
            if match:
                name = match.group(1).strip()
                # Clean up
                name = re.sub(r'\s+', ' ', name)
                if len(name) > 2:
                    return name[:50]  # Limit length

        return None
