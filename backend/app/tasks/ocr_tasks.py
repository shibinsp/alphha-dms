import os
import logging
import asyncio
from typing import Optional

from app.tasks import celery_app
from app.core.database import SessionLocal
from app.models.document import Document, OCRStatus
from app.core.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def process_ocr(self, document_id: str) -> dict:
    """
    Process OCR for a document using Mistral AI or fallback to Tesseract.
    """
    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.error(f"Document {document_id} not found")
            return {"status": "error", "message": "Document not found"}

        # Update status to processing
        document.ocr_status = OCRStatus.PROCESSING
        db.commit()

        # Get file path
        file_path = document.file_path
        if not os.path.exists(file_path):
            document.ocr_status = OCRStatus.FAILED
            db.commit()
            return {"status": "error", "message": "File not found"}

        try:
            mime_type = document.mime_type
            
            # Read file content
            with open(file_path, "rb") as f:
                file_content = f.read()
            
            # Try Mistral AI first if API key is configured
            if settings.MISTRAL_API_KEY and mime_type.startswith("image/"):
                result = asyncio.run(process_with_mistral(file_content, document.file_name, mime_type))
                if result.get("success"):
                    document.ocr_text = result.get("text", "")
                    document.ocr_confidence = result.get("confidence", 0)
                    document.extracted_metadata = {
                        "document_type": result.get("document_type"),
                        "language": result.get("language"),
                        "entities": result.get("entities", {}),
                        "metadata": result.get("metadata", {}),
                        "confidence": result.get("confidence", 0)
                    }
                    document.ocr_status = OCRStatus.COMPLETED
                    db.commit()

                    # Trigger embedding generation after Mistral OCR
                    from app.tasks.embedding_tasks import generate_document_embedding
                    generate_document_embedding.delay(document_id, document.tenant_id)

                    logger.info(f"Mistral OCR completed for document {document_id}")
                    return {"status": "success", "method": "mistral", "text_length": len(document.ocr_text)}
            
            # Fallback to traditional OCR
            text = ""
            if mime_type == "application/pdf":
                text = extract_pdf_text(file_path)
            elif mime_type.startswith("image/"):
                text = extract_image_text(file_path)
            else:
                document.ocr_status = OCRStatus.COMPLETED
                document.ocr_text = ""
                db.commit()
                return {"status": "success", "message": "No OCR needed for this file type"}

            document.ocr_text = text
            document.ocr_status = OCRStatus.COMPLETED
            db.commit()

            # Trigger embedding generation after OCR
            from app.tasks.embedding_tasks import generate_document_embedding
            generate_document_embedding.delay(document_id, document.tenant_id)

            logger.info(f"OCR completed for document {document_id}")
            return {"status": "success", "method": "tesseract", "text_length": len(text)}

        except Exception as e:
            logger.error(f"OCR failed for document {document_id}: {str(e)}")
            document.ocr_status = OCRStatus.FAILED
            db.commit()
            raise self.retry(exc=e, countdown=60)

    finally:
        db.close()


async def process_with_mistral(file_content: bytes, file_name: str, mime_type: str) -> dict:
    """Process document with Mistral AI for OCR and metadata extraction."""
    try:
        from app.services.mistral_ocr_service import MistralOCRService
        return await MistralOCRService.extract_text_and_metadata(file_content, file_name, mime_type)
    except Exception as e:
        logger.error(f"Mistral OCR error: {e}")
        return {"success": False, "error": str(e)}


def extract_pdf_text(file_path: str) -> str:
    """Extract text from PDF using PyPDF2 and OCR for scanned pages."""
    try:
        import PyPDF2
        from pdf2image import convert_from_path
        import pytesseract

        text_parts = []

        # First try direct text extraction
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        # If no text found, try OCR on images
        if not text_parts or all(not t.strip() for t in text_parts):
            images = convert_from_path(file_path)
            for image in images:
                text = pytesseract.image_to_string(image, lang="eng+ara")
                if text.strip():
                    text_parts.append(text)

        return "\n\n".join(text_parts)

    except ImportError as e:
        logger.warning(f"PDF processing dependencies not installed: {e}")
        return ""
    except Exception as e:
        logger.error(f"PDF text extraction failed: {e}")
        return ""


def extract_image_text(file_path: str) -> str:
    """Extract text from image using Tesseract OCR."""
    try:
        import pytesseract
        from PIL import Image

        image = Image.open(file_path)
        text = pytesseract.image_to_string(image, lang="eng+ara")
        return text

    except ImportError as e:
        logger.warning(f"Image OCR dependencies not installed: {e}")
        return ""
    except Exception as e:
        logger.error(f"Image OCR failed: {e}")
        return ""
