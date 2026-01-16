"""Mistral AI OCR and Metadata Extraction Service."""
import httpx
import base64
import json
import io
from typing import Dict, Any
from app.core.config import settings


def extract_pdf_text(file_content: bytes) -> str:
    """Extract text from PDF using PyPDF2, fallback to Tesseract OCR."""
    text = ""
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        text = text.strip()
        
        if len(text) > 50:
            print(f"PyPDF2 extracted {len(text)} chars")
            return text
    except Exception as e:
        print(f"PyPDF2 extraction failed: {e}")
    
    # Fallback to Tesseract OCR for scanned PDFs
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
        
        print("Falling back to Tesseract OCR...")
        images = convert_from_bytes(file_content, dpi=200)
        ocr_text = ""
        for i, img in enumerate(images):
            print(f"Processing page {i+1}/{len(images)}")
            try:
                page_text = pytesseract.image_to_string(img, lang='eng')
            except Exception:
                page_text = pytesseract.image_to_string(img)
            ocr_text += page_text + "\n"
        if ocr_text.strip():
            print(f"Tesseract extracted {len(ocr_text)} chars")
            return ocr_text.strip()
    except Exception as e:
        print(f"Tesseract OCR failed: {e}")
    
    return text


def extract_image_text(file_content: bytes) -> str:
    """Extract text from image using Tesseract OCR."""
    try:
        import pytesseract
        from PIL import Image
        
        img = Image.open(io.BytesIO(file_content))
        text = pytesseract.image_to_string(img, lang='eng')
        print(f"Image OCR extracted {len(text)} chars")
        return text.strip()
    except Exception as e:
        print(f"Image OCR failed: {e}")
        return ""


class MistralOCRService:
    """Service for OCR and metadata extraction using Mistral AI."""
    
    BASE_URL = "https://api.mistral.ai/v1"
    
    @staticmethod
    async def extract_text_and_metadata(
        file_content: bytes,
        file_name: str,
        mime_type: str
    ) -> Dict[str, Any]:
        """Extract text and metadata from document using local OCR + optional Mistral AI."""
        
        print(f"Starting extraction for {file_name} ({mime_type})")
        
        # First, extract text locally
        extracted_text = ""
        is_image = mime_type.startswith("image/")
        
        if mime_type == "application/pdf":
            extracted_text = extract_pdf_text(file_content)
        elif is_image:
            extracted_text = extract_image_text(file_content)
        
        print(f"Local extraction got {len(extracted_text)} chars")
        
        # If we have text, try to analyze with Mistral AI for metadata
        if extracted_text and settings.MISTRAL_API_KEY:
            try:
                metadata = await MistralOCRService._analyze_with_mistral(extracted_text, file_name)
                return {
                    "text": extracted_text,
                    "document_type": metadata.get("document_type", "unknown"),
                    "language": metadata.get("language", "en"),
                    "confidence": metadata.get("confidence", 85),
                    "entities": metadata.get("entities", {}),
                    "metadata": metadata.get("metadata", {}),
                    "success": True
                }
            except Exception as e:
                print(f"Mistral analysis failed: {e}, using local extraction only")
        
        # Return local extraction result even without Mistral
        if extracted_text:
            return {
                "text": extracted_text,
                "document_type": "unknown",
                "language": "en",
                "confidence": 70,
                "entities": {},
                "metadata": {"source": "local_ocr"},
                "success": True
            }
        
        # If no local text and we have Mistral, try vision API for images
        if is_image and settings.MISTRAL_API_KEY:
            try:
                return await MistralOCRService._extract_with_vision(file_content, file_name, mime_type)
            except Exception as e:
                print(f"Vision API failed: {e}")
        
        return {
            "text": "",
            "metadata": {},
            "error": "Could not extract text from document",
            "success": False
        }
    
    @staticmethod
    async def _analyze_with_mistral(text: str, file_name: str) -> Dict[str, Any]:
        """Analyze extracted text with Mistral AI for metadata extraction."""
        prompt = f"""Analyze this document text and extract metadata.
Document filename: {file_name}

Text content:
{text[:6000]}

Return JSON:
{{
    "document_type": "invoice/contract/id_document/bank_statement/letter/report/other",
    "language": "en/ar/etc",
    "confidence": 85,
    "entities": {{
        "names": [],
        "dates": [],
        "amounts": [],
        "addresses": [],
        "id_numbers": [],
        "organizations": []
    }},
    "metadata": {{
        "title": "",
        "subject": "",
        "keywords": []
    }}
}}"""

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{MistralOCRService.BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": settings.MISTRAL_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"}
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                return json.loads(content)
            else:
                print(f"Mistral API error: {response.status_code} - {response.text}")
                raise Exception(f"API error: {response.status_code}")
    
    @staticmethod
    async def _extract_with_vision(file_content: bytes, file_name: str, mime_type: str) -> Dict[str, Any]:
        """Use Mistral vision API for image OCR."""
        prompt = """Extract all text from this image and analyze it.
Return JSON:
{
    "extracted_text": "all text found in image",
    "document_type": "type",
    "language": "en/ar/etc",
    "confidence": 85,
    "entities": {
        "names": [],
        "dates": [],
        "amounts": [],
        "id_numbers": []
    }
}"""
        
        b64_content = base64.b64encode(file_content).decode()
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{MistralOCRService.BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "pixtral-12b-2409",
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64_content}"}}
                        ]
                    }],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"}
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                return {
                    "text": parsed.get("extracted_text", ""),
                    "document_type": parsed.get("document_type", "unknown"),
                    "language": parsed.get("language", "en"),
                    "confidence": parsed.get("confidence", 80),
                    "entities": parsed.get("entities", {}),
                    "metadata": {},
                    "success": True
                }
            else:
                raise Exception(f"Vision API error: {response.status_code}")

    @staticmethod
    async def analyze_bank_statement(file_content: bytes, mime_type: str) -> Dict[str, Any]:
        """Specialized analysis for bank statements."""
        
        if not settings.MISTRAL_API_KEY:
            return {"error": "Mistral API key not configured"}
        
        # First extract text
        if mime_type == "application/pdf":
            text = extract_pdf_text(file_content)
        elif mime_type.startswith("image/"):
            text = extract_image_text(file_content)
        else:
            text = ""
        
        prompt = f"""Analyze this bank statement and extract:
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

Bank Statement Text:
{text[:8000]}

Return JSON:
{{
    "account_holder": "",
    "account_number": "****1234",
    "bank_name": "",
    "period": {{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}},
    "opening_balance": 0.00,
    "closing_balance": 0.00,
    "total_credits": 0.00,
    "total_debits": 0.00,
    "transactions": [
        {{"date": "", "description": "", "type": "credit/debit", "amount": 0.00, "balance": 0.00, "category": ""}}
    ],
    "salary_detected": true,
    "monthly_salary": 0.00,
    "flags": []
}}"""

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    f"{MistralOCRService.BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": settings.MISTRAL_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
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
