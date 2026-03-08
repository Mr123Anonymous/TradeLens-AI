"""
Main Pipeline - Orchestrates the entire document processing workflow
"""
from pathlib import Path
from typing import Dict, Optional
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.pdf_extractor import PDFExtractor
from src.llm_extractor import LLMExtractor
from src.data_storage import DataStorage
from src.semantic_search import SemanticSearch
from config import Config

class DocumentPipeline:
    """End-to-end document processing pipeline"""
    
    def __init__(self, use_ocr: bool = False):
        """
        Initialize pipeline
        
        Args:
            use_ocr: Whether to use OCR for scanned PDFs
        """
        print("Initializing Document Intelligence Pipeline...")
        
        self.pdf_extractor = PDFExtractor(use_ocr=use_ocr)
        self.llm_extractor = LLMExtractor()
        self.storage = DataStorage()
        self.search = SemanticSearch()
        
        print("✓ Pipeline initialized successfully")
    
    def process_document(self, pdf_path: Path, save_formats: list = ["json", "csv", "db"]) -> Dict:
        """
        Process a single PDF document through the entire pipeline
        
        Args:
            pdf_path: Path to PDF file
            save_formats: Formats to save extracted data
            
        Returns:
            Dictionary with processing results
        """
        print(f"\n{'='*60}")
        print(f"Processing: {pdf_path.name}")
        print(f"{'='*60}")
        
        result = {
            "success": False,
            "file_name": pdf_path.name,
            "errors": []
        }
        
        try:
            # Step 1: Extract text from PDF
            print("\n[1/4] Extracting text from PDF...")
            extraction_result = self.pdf_extractor.extract_text(pdf_path)
            
            extracted_text = extraction_result["text"]
            print(f"✓ Extracted {len(extracted_text)} characters using {extraction_result['extraction_method']}")
            
            if len(extracted_text) < 20:
                raise Exception("Extracted text too short. PDF may be empty or corrupted.")
            
            # Step 2: Extract structured data using LLM
            print("\n[2/4] Extracting structured fields with LLM...")
            structured_data = self.llm_extractor.extract(extracted_text)
            print(f"✓ Extracted fields: {', '.join(structured_data.keys())}")
            
            # Validate extraction
            validation = self.llm_extractor.validate_extraction(structured_data)
            if not validation["is_valid"]:
                print(f"⚠ Warning: Missing fields: {', '.join(validation['missing_fields'])}")
            
            # Step 3: Save to storage
            print("\n[3/4] Saving to storage...")
            
            # Combine all data
            complete_data = {
                **structured_data,
                "file_name": pdf_path.name,
                "raw_text": extracted_text,
                "extraction_method": extraction_result["extraction_method"],
                "page_count": extraction_result["page_count"]
            }
            
            save_results = self.storage.save(complete_data, formats=save_formats)
            print(f"✓ Saved to: {', '.join(save_formats)}")
            
            # Step 4: Add to semantic search index
            print("\n[4/4] Adding to search index...")
            self.search.add_documents([complete_data])
            print("✓ Added to search index")
            
            # Prepare result
            result.update({
                "success": True,
                "extracted_data": structured_data,
                "text_length": len(extracted_text),
                "extraction_method": extraction_result["extraction_method"],
                "page_count": extraction_result["page_count"],
                "storage_results": save_results,
                "validation": validation
            })
            
            print(f"\n{'='*60}")
            print(f"✓ Successfully processed: {pdf_path.name}")
            print(f"{'='*60}\n")
        
        except Exception as e:
            error_msg = str(e)
            result["errors"].append(error_msg)
            print(f"\n✗ Error processing {pdf_path.name}: {error_msg}\n")
        
        return result
    
    def process_directory(self, directory: Path, pattern: str = "*.pdf") -> Dict:
        """
        Process all PDFs in a directory
        
        Args:
            directory: Path to directory
            pattern: File pattern to match
            
        Returns:
            Dictionary with processing statistics
        """
        pdf_files = list(directory.glob(pattern))
        
        print(f"\nFound {len(pdf_files)} PDF files in {directory}")
        
        results = {
            "total": len(pdf_files),
            "successful": 0,
            "failed": 0,
            "details": []
        }
        
        for pdf_file in pdf_files:
            result = self.process_document(pdf_file)
            results["details"].append(result)
            
            if result["success"]:
                results["successful"] += 1
            else:
                results["failed"] += 1
        
        print(f"\n{'='*60}")
        print(f"Batch Processing Complete")
        print(f"{'='*60}")
        print(f"Total: {results['total']}")
        print(f"Successful: {results['successful']}")
        print(f"Failed: {results['failed']}")
        print(f"{'='*60}\n")
        
        return results
    
    def rebuild_search_index(self):
        """Rebuild search index from stored data"""
        print("Rebuilding search index from database...")
        
        # Clear existing index
        self.search.clear_index()
        
        # Load all invoices from database
        invoices = self.storage.load_all(format="db")
        
        if invoices:
            # Add to search index
            self.search.add_documents(invoices)
            print(f"✓ Rebuilt search index with {len(invoices)} documents")
        else:
            print("No documents found in database")
