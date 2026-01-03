"""Mistral AI OCR and Metadata Extraction Service."""
import httpx
import base64
import json
from typing import Optional, Dict, Any
from app.core.config import settings


class MistralOCRService:
    """Service for OCR and metadata extraction using Mistral AI."""
    
    BASE_URL = "https://api.mistral.ai/v1"
    
    @staticmethod
    async def extract_text_and_metadata(
        file_content: bytes,
        file_name: str,
        mime_type: str
    ) -> Dict[str, Any]:
        """Extract text and metadata from document using Mistral AI."""
        
        if not settings.MISTRAL_API_KEY:
            return {"text": "", "metadata": {}, "error": "Mistral API key not configured"}
        
        # Encode file to base64 for image types
        is_image = mime_type.startswith("image/")
        
        prompt = """Analyze this document and extract:
1. All text content (OCR if image)
2. Document type (invoice, contract, ID, bank statement, etc.)
3. Key entities (names, dates, amounts, addresses, IDs)
4. Language detected
5. Confidence score (0-100)

Return JSON format:
{
    "extracted_text": "full text here",
    "document_type": "type",
    "language": "en/ar/etc",
    "confidence": 85,
    "entities": {
        "names": [],
        "dates": [],
        "amounts": [],
        "addresses": [],
        "id_numbers": [],
        "organizations": []
    },
    "metadata": {
        "title": "",
        "author": "",
        "subject": "",
        "keywords": []
    }
}"""

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                if is_image:
                    # Use vision endpoint for images
                    b64_content = base64.b64encode(file_content).decode()
                    messages = [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{mime_type};base64,{b64_content}"
                                    }
                                }
                            ]
                        }
                    ]
                    model = "pixtral-12b-2409"
                else:
                    # For PDFs/docs, use text description
                    messages = [
                        {
                            "role": "user", 
                            "content": f"{prompt}\n\nDocument filename: {file_name}\nMIME type: {mime_type}\n\nNote: For non-image documents, provide analysis based on filename and type."
                        }
                    ]
                    model = settings.MISTRAL_MODEL
                
                response = await client.post(
                    f"{MistralOCRService.BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": 0.1,
                        "response_format": {"type": "json_object"}
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    try:
                        parsed = json.loads(content)
                        return {
                            "text": parsed.get("extracted_text", ""),
                            "document_type": parsed.get("document_type", "unknown"),
                            "language": parsed.get("language", "en"),
                            "confidence": parsed.get("confidence", 0),
                            "entities": parsed.get("entities", {}),
                            "metadata": parsed.get("metadata", {}),
                            "success": True
                        }
                    except json.JSONDecodeError:
                        return {"text": content, "metadata": {}, "success": True}
                else:
                    return {
                        "text": "",
                        "metadata": {},
                        "error": f"API error: {response.status_code}",
                        "success": False
                    }
                    
        except Exception as e:
            return {"text": "", "metadata": {}, "error": str(e), "success": False}

    @staticmethod
    async def analyze_bank_statement(file_content: bytes, mime_type: str) -> Dict[str, Any]:
        """Specialized analysis for bank statements."""
        
        if not settings.MISTRAL_API_KEY:
            return {"error": "Mistral API key not configured"}
        
        prompt = """Analyze this bank statement and extract:
1. Account holder name
2. Account number (mask middle digits)
3. Bank name
4. Statement period (start and end dates)
5. Opening balance
6. Closing balance
7. All transactions with: date, description, debit/credit, amount, balance
8. Total credits and debits
9. Identify salary credits
10. Flag any suspicious transactions

Return JSON:
{
    "account_holder": "",
    "account_number": "****1234",
    "bank_name": "",
    "period": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
    "opening_balance": 0.00,
    "closing_balance": 0.00,
    "total_credits": 0.00,
    "total_debits": 0.00,
    "transactions": [
        {"date": "", "description": "", "type": "credit/debit", "amount": 0.00, "balance": 0.00, "category": ""}
    ],
    "salary_detected": true,
    "monthly_salary": 0.00,
    "flags": []
}"""

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                is_image = mime_type.startswith("image/")
                
                if is_image:
                    b64_content = base64.b64encode(file_content).decode()
                    messages = [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64_content}"}}
                            ]
                        }
                    ]
                    model = "pixtral-12b-2409"
                else:
                    messages = [{"role": "user", "content": prompt}]
                    model = settings.MISTRAL_MODEL
                
                response = await client.post(
                    f"{MistralOCRService.BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": 0.1,
                        "response_format": {"type": "json_object"}
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    return json.loads(content)
                else:
                    return {"error": f"API error: {response.status_code}"}
                    
        except Exception as e:
            return {"error": str(e)}
