import os
import logging
from typing import Optional

from app.tasks import celery_app
from app.core.database import SessionLocal
from app.models.document import Document, OCRStatus

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def process_ocr(self, document_id: str) -> dict:
    """
    Process OCR for a document.
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
            # Extract text based on file type
            mime_type = document.mime_type
            text = ""

            if mime_type == "application/pdf":
                text = extract_pdf_text(file_path)
            elif mime_type.startswith("image/"):
                text = extract_image_text(file_path)
            else:
                # For other types, skip OCR
                document.ocr_status = OCRStatus.COMPLETED
                document.ocr_text = ""
                db.commit()
                return {"status": "success", "message": "No OCR needed for this file type"}

            # Update document with OCR text
            document.ocr_text = text
            document.ocr_status = OCRStatus.COMPLETED
            db.commit()

            logger.info(f"OCR completed for document {document_id}")
            return {"status": "success", "text_length": len(text)}

        except Exception as e:
            logger.error(f"OCR failed for document {document_id}: {str(e)}")
            document.ocr_status = OCRStatus.FAILED
            db.commit()
            raise self.retry(exc=e, countdown=60)

    finally:
        db.close()


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
