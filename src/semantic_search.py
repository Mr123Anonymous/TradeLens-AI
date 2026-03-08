"""
Semantic Search Module using Embeddings and FAISS
"""
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import pickle
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from config import Config

class SemanticSearch:
    """Semantic search over invoice documents using embeddings"""
    
    def __init__(self, model_name: Optional[str] = None, vector_db_path: Optional[Path] = None):
        """
        Initialize semantic search
        
        Args:
            model_name: Name of sentence transformer model
            vector_db_path: Path to vector database storage
        """
        self.model_name = model_name or Config.EMBEDDING_MODEL
        self.vector_db_path = vector_db_path or Config.VECTOR_DB_PATH
        self.vector_db_path.mkdir(parents=True, exist_ok=True)
        
        # Load embedding model
        print(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        
        # Initialize FAISS index
        self.index = None
        self.documents = []
        self.metadata = []
        
        # Paths for persistence
        self.index_file = self.vector_db_path / "faiss_index.bin"
        self.metadata_file = self.vector_db_path / "metadata.pkl"
        
        # Load existing index if available
        self.load_index()
    
    def create_document_text(self, invoice_data: Dict) -> str:
        """
        Create searchable text representation of invoice
        
        Args:
            invoice_data: Invoice data dictionary
            
        Returns:
            Concatenated text for embedding
        """
        parts = []
        
        # Add all relevant fields
        if invoice_data.get("invoice_number"):
            parts.append(f"Invoice Number: {invoice_data['invoice_number']}")
        
        if invoice_data.get("seller_name"):
            parts.append(f"Seller: {invoice_data['seller_name']}")
        
        if invoice_data.get("buyer_name"):
            parts.append(f"Buyer: {invoice_data['buyer_name']}")
        
        if invoice_data.get("total_amount") and invoice_data.get("currency"):
            parts.append(f"Amount: {invoice_data['total_amount']} {invoice_data['currency']}")
        
        if invoice_data.get("invoice_date"):
            parts.append(f"Date: {invoice_data['invoice_date']}")
        
        # Add raw text if available (for content-based search)
        if invoice_data.get("raw_text"):
            parts.append(invoice_data["raw_text"][:500])  # First 500 chars
        
        return " | ".join(parts)
    
    def add_documents(self, invoices: List[Dict]) -> int:
        """
        Add invoices to the search index
        
        Args:
            invoices: List of invoice dictionaries
            
        Returns:
            Number of documents added
        """
        if not invoices:
            return 0
        
        # Filter out empty/invalid invoices
        valid_invoices = [inv for inv in invoices if self._is_valid_invoice(inv)]
        skipped = len(invoices) - len(valid_invoices)
        
        if skipped > 0:
            print(f"Skipping {skipped} empty/invalid invoices")
        
        if not valid_invoices:
            print("No valid invoices to add")
            return 0
        
        # Create document texts
        texts = [self.create_document_text(inv) for inv in valid_invoices]
        
        # Generate embeddings
        print(f"Generating embeddings for {len(texts)} valid documents...")
        embeddings = self.model.encode(texts, show_progress_bar=True)
        embeddings = np.array(embeddings).astype('float32')
        
        # Initialize or expand FAISS index
        if self.index is None:
            # Create new index
            self.index = faiss.IndexFlatL2(self.embedding_dim)
        
        # Add embeddings to index
        self.index.add(embeddings)  # type: ignore[call-arg]
        
        # Store documents and metadata
        self.documents.extend(texts)
        self.metadata.extend(valid_invoices)
        
        print(f"Added {len(invoices)} documents to index. Total: {self.index.ntotal}")
        
        # Save index
        self.save_index()
        
        return len(invoices)
    
    def search(self, query: str, top_k: int = 5, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Search for similar invoices
        
        Args:
            query: Search query
            top_k: Number of results to return
            filters: Optional filters (min_amount, currency, etc.)
            
        Returns:
            List of matching invoices with scores
        """
        if self.index is None or self.index.ntotal == 0:
            return []
        
        # Generate query embedding
        query_embedding = self.model.encode([query])
        query_embedding = np.array(query_embedding).astype('float32')
        
        # Search in FAISS
        # Get more results than needed for post-filtering
        search_k = min(top_k * 5, self.index.ntotal)  # Get more candidates for filtering
        distances, indices = self.index.search(query_embedding, search_k)  # type: ignore[call-arg]
        
        # Prepare results
        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < len(self.metadata):
                invoice_data = self.metadata[idx]
                
                # Skip empty/invalid invoices (all None values)
                if not self._is_valid_invoice(invoice_data):
                    continue
                
                result = {
                    "rank": i + 1,
                    "score": float(1 / (1 + dist)),  # Convert distance to similarity score
                    "distance": float(dist),
                    "invoice": invoice_data,
                    "matched_text": self.documents[idx]
                }
                
                # Apply filters if provided
                if filters:
                    if not self._apply_filters(result["invoice"], filters):
                        continue
                
                results.append(result)
                
                # Stop if we have enough results
                if len(results) >= top_k:
                    break
        
        return results
    
    def _is_valid_invoice(self, invoice: Dict) -> bool:
        """
        Check if invoice has meaningful data (not just empty template)
        
        Args:
            invoice: Invoice data dictionary
            
        Returns:
            True if invoice has at least some real data
        """
        # Check if at least 2 of these key fields have values
        key_fields = [
            invoice.get("invoice_number"),
            invoice.get("seller_name"),
            invoice.get("buyer_name"),
            invoice.get("total_amount")
        ]
        
        non_null_count = sum(1 for field in key_fields if field is not None and str(field).strip() and str(field) != "None" and str(field) != "0" and str(field) != "0.0")
        
        return non_null_count >= 2  # At least 2 meaningful fields
    
    def _apply_filters(self, invoice: Dict, filters: Dict) -> bool:
        """Apply filters to invoice"""
        if "min_amount" in filters:
            amount = self._parse_amount(invoice.get("total_amount"))
            if amount is None or amount < filters["min_amount"]:
                return False
        
        if "max_amount" in filters:
            amount = self._parse_amount(invoice.get("total_amount"))
            if amount is None or amount > filters["max_amount"]:
                return False
        
        if "currency" in filters:
            if invoice.get("currency") != filters["currency"]:
                return False
        
        if "exclude_currency" in filters:
            if invoice.get("currency") == filters["exclude_currency"]:
                return False
        
        if "seller_name" in filters:
            seller = invoice.get("seller_name", "").lower()
            if filters["seller_name"].lower() not in seller:
                return False
        
        if "buyer_name" in filters:
            buyer = invoice.get("buyer_name", "").lower()
            if filters["buyer_name"].lower() not in buyer:
                return False
        
        return True
    
    def _parse_amount(self, amount: Any) -> Optional[float]:
        """Parse amount to float"""
        if amount is None:
            return None
        try:
            return float(str(amount).replace(",", "").replace("$", "").strip())
        except (ValueError, AttributeError):
            return None
    
    def save_index(self):
        """Save FAISS index and metadata to disk"""
        if self.index is not None:
            faiss.write_index(self.index, str(self.index_file))
        
        with open(self.metadata_file, 'wb') as f:
            pickle.dump({
                'documents': self.documents,
                'metadata': self.metadata
            }, f)
        
        print(f"Index saved to {self.index_file}")
    
    def load_index(self):
        """Load FAISS index and metadata from disk"""
        if self.index_file.exists() and self.metadata_file.exists():
            try:
                self.index = faiss.read_index(str(self.index_file))
                
                with open(self.metadata_file, 'rb') as f:
                    data = pickle.load(f)
                    self.documents = data['documents']
                    self.metadata = data['metadata']
                
                print(f"Loaded index with {self.index.ntotal} documents")
            except Exception as e:
                print(f"Failed to load index: {e}")
                self.index = None
    
    def clear_index(self):
        """Clear the search index"""
        self.index = None
        self.documents = []
        self.metadata = []
        
        # Remove files
        if self.index_file.exists():
            self.index_file.unlink()
        if self.metadata_file.exists():
            self.metadata_file.unlink()
        
        print("Index cleared")
    
    def get_statistics(self) -> Dict:
        """Get index statistics"""
        return {
            "total_documents": len(self.documents),
            "embedding_dimension": self.embedding_dim,
            "model_name": self.model_name,
            "index_size": self.index.ntotal if self.index else 0
        }
