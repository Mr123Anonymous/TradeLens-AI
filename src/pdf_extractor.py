"""
PDF Text Extraction Module
Supports both digital and scanned PDFs
"""
import fitz  # PyMuPDF - pip install PyMuPDF  # type: ignore[import-untyped]
import pdfplumber
from pathlib import Path
from typing import Optional, Dict, Any
import pytesseract
from PIL import Image
import io

class PDFExtractor:
    """Extract text from PDF documents"""
    
    def __init__(self, use_ocr: bool = False):
        """
        Initialize PDF extractor
        
        Args:
            use_ocr: If True, will attempt OCR on scanned PDFs
        """
        self.use_ocr = use_ocr
    
    def extract_with_pymupdf(self, pdf_path: Path) -> str:
        """
        Extract text using PyMuPDF (fast, good for digital PDFs)
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text
        """
        try:
            doc = fitz.open(pdf_path)
            text = ""
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text += str(page.get_text("text"))
            
            doc.close()
            return text.strip()
        
        except Exception as e:
            raise Exception(f"PyMuPDF extraction failed: {str(e)}")
    
    def extract_with_pdfplumber(self, pdf_path: Path) -> str:
        """
        Extract text using pdfplumber (better table handling)
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text
        """
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            return text.strip()
        
        except Exception as e:
            raise Exception(f"pdfplumber extraction failed: {str(e)}")
    
    def extract_with_ocr(self, pdf_path: Path) -> str:
        """
        Extract text using OCR (for scanned PDFs)
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text
        """
        try:
            doc = fitz.open(pdf_path)
            text = ""
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                
                # Convert page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                
                # Perform OCR
                page_text = pytesseract.image_to_string(img)
                text += page_text + "\n"
            
            doc.close()
            return text.strip()
        
        except Exception as e:
            raise Exception(f"OCR extraction failed: {str(e)}")
    
    def extract_text(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Main extraction method with fallback strategy
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with extracted text and metadata
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Try PyMuPDF first (fastest)
        text = self.extract_with_pymupdf(pdf_path)
        method = "pymupdf"
        
        # If text is too short, try pdfplumber
        if len(text) < 50:
            text = self.extract_with_pdfplumber(pdf_path)
            method = "pdfplumber"
        
        # If still too short and OCR is enabled, try OCR
        if len(text) < 50 and self.use_ocr:
            text = self.extract_with_ocr(pdf_path)
            method = "ocr"
        
        # Get metadata
        doc = fitz.open(pdf_path)
        page_count = doc.page_count
        metadata = doc.metadata
        doc.close()
        
        return {
            "text": text,
            "page_count": page_count,
            "extraction_method": method,
            "file_name": pdf_path.name,
            "metadata": metadata
        }
    
    def extract_text_by_page(self, pdf_path: Path) -> Dict[int, str]:
        """
        Extract text page by page
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary mapping page number to text
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        doc = fitz.open(pdf_path)
        pages = {}
        
        for page_num in range(doc.page_count):
            page = doc[page_num]
            pages[page_num + 1] = page.get_text()
        
        doc.close()
        return pages
