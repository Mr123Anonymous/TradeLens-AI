"""
Data Storage Module
Handles storage of extracted data in JSON, CSV, and SQLite
"""
import json
import csv
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd
from config import Config

class DataStorage:
    """Manage storage of extracted invoice data"""
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize data storage
        
        Args:
            storage_path: Path to storage directory
        """
        self.storage_path = storage_path or Config.DATA_STORAGE_PATH
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.json_file = self.storage_path / "invoices.json"
        self.csv_file = self.storage_path / "invoices.csv"
        self.db_file = self.storage_path / "invoices.db"
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Create SQLite database and tables"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT,
                invoice_date TEXT,
                seller_name TEXT,
                buyer_name TEXT,
                total_amount REAL,
                currency TEXT,
                file_name TEXT,
                extracted_at TEXT,
                raw_text TEXT,
                extraction_method TEXT,
                UNIQUE(invoice_number, file_name)
            )
        """)
        
        # Create index for faster searches
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_invoice_number 
            ON invoices(invoice_number)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_seller_name 
            ON invoices(seller_name)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_total_amount 
            ON invoices(total_amount)
        """)
        
        conn.commit()
        conn.close()
    
    def save_to_json(self, data: Dict, append: bool = True) -> Path:
        """
        Save data to JSON file
        
        Args:
            data: Data dictionary to save
            append: If True, append to existing file
            
        Returns:
            Path to saved file
        """
        # Add timestamp
        data["extracted_at"] = datetime.now().isoformat()
        
        if append and self.json_file.exists():
            # Load existing data
            with open(self.json_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            
            # Ensure it's a list
            if not isinstance(existing_data, list):
                existing_data = [existing_data]
            
            existing_data.append(data)
            
            # Save merged data
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, indent=2, ensure_ascii=False)
        else:
            # Save as new file (list format for consistency)
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump([data], f, indent=2, ensure_ascii=False)
        
        return self.json_file
    
    def save_to_csv(self, data: Dict) -> Path:
        """
        Save data to CSV file
        
        Args:
            data: Data dictionary to save
            
        Returns:
            Path to saved file
        """
        # Add timestamp
        data["extracted_at"] = datetime.now().isoformat()
        
        # Flatten nested data if any
        flat_data = self._flatten_dict(data)
        
        # Check if file exists
        file_exists = self.csv_file.exists()
        
        # Write to CSV
        with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=flat_data.keys())
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow(flat_data)
        
        return self.csv_file
    
    def save_to_database(self, data: Dict) -> int:
        """
        Save data to SQLite database
        
        Args:
            data: Data dictionary to save
            
        Returns:
            ID of inserted record
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Prepare data
        invoice_data = {
            "invoice_number": data.get("invoice_number"),
            "invoice_date": data.get("invoice_date"),
            "seller_name": data.get("seller_name"),
            "buyer_name": data.get("buyer_name"),
            "total_amount": self._parse_amount(data.get("total_amount")),
            "currency": data.get("currency"),
            "file_name": data.get("file_name"),
            "extracted_at": datetime.now().isoformat(),
            "raw_text": data.get("raw_text", ""),
            "extraction_method": data.get("extraction_method", "")
        }
        
        try:
            cursor.execute("""
                INSERT INTO invoices (
                    invoice_number, invoice_date, seller_name, buyer_name,
                    total_amount, currency, file_name, extracted_at,
                    raw_text, extraction_method
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, tuple(invoice_data.values()))
            
            conn.commit()
            row_id = cursor.lastrowid if cursor.lastrowid is not None else 0
        
        except sqlite3.IntegrityError:
            # Update existing record instead
            cursor.execute("""
                UPDATE invoices SET
                    invoice_date = ?,
                    seller_name = ?,
                    buyer_name = ?,
                    total_amount = ?,
                    currency = ?,
                    extracted_at = ?,
                    raw_text = ?,
                    extraction_method = ?
                WHERE invoice_number = ? AND file_name = ?
            """, (
                invoice_data["invoice_date"],
                invoice_data["seller_name"],
                invoice_data["buyer_name"],
                invoice_data["total_amount"],
                invoice_data["currency"],
                invoice_data["extracted_at"],
                invoice_data["raw_text"],
                invoice_data["extraction_method"],
                invoice_data["invoice_number"],
                invoice_data["file_name"]
            ))
            conn.commit()
            row_id = cursor.lastrowid if cursor.lastrowid is not None else 0
        
        finally:
            conn.close()
        
        return row_id
    
    def save(self, data: Dict, formats: List[str] = ["json", "csv", "db"]) -> Dict[str, Any]:
        """
        Save data to multiple formats
        
        Args:
            data: Data dictionary to save
            formats: List of formats to save to
            
        Returns:
            Dictionary with save results
        """
        results = {}
        
        if "json" in formats:
            results["json"] = str(self.save_to_json(data))
        
        if "csv" in formats:
            results["csv"] = str(self.save_to_csv(data))
        
        if "db" in formats:
            results["db_id"] = self.save_to_database(data)
        
        return results
    
    def load_all(self, format: str = "db") -> List[Dict]:
        """
        Load all stored data
        
        Args:
            format: Format to load from (json, csv, or db)
            
        Returns:
            List of data dictionaries
        """
        if format == "json":
            if self.json_file.exists():
                with open(self.json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else [data]
            return []
        
        elif format == "csv":
            if self.csv_file.exists():
                df = pd.read_csv(self.csv_file)
                return df.to_dict('records')
            return []
        
        elif format == "db":
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM invoices ORDER BY extracted_at DESC")
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def search(self, query: Dict) -> List[Dict]:
        """
        Search invoices in database
        
        Args:
            query: Dictionary with search criteria
            
        Returns:
            List of matching invoices
        """
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Build WHERE clause
        conditions = []
        params = []
        
        if "invoice_number" in query:
            conditions.append("invoice_number LIKE ?")
            params.append(f"%{query['invoice_number']}%")
        
        if "seller_name" in query:
            conditions.append("seller_name LIKE ?")
            params.append(f"%{query['seller_name']}%")
        
        if "buyer_name" in query:
            conditions.append("buyer_name LIKE ?")
            params.append(f"%{query['buyer_name']}%")
        
        if "min_amount" in query:
            conditions.append("total_amount >= ?")
            params.append(query["min_amount"])
        
        if "max_amount" in query:
            conditions.append("total_amount <= ?")
            params.append(query["max_amount"])
        
        if "currency" in query:
            conditions.append("currency = ?")
            params.append(query["currency"])
        
        # Execute query
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM invoices WHERE {where_clause} ORDER BY extracted_at DESC"
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def delete_by_id(self, doc_id: int) -> bool:
        """
        Delete a document by ID
        
        Args:
            doc_id: Document ID to delete
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM invoices WHERE id = ?", (doc_id,))
            conn.commit()
            deleted = cursor.rowcount > 0
            conn.close()
            return deleted
        except Exception as e:
            print(f"Error deleting document {doc_id}: {e}")
            return False
    
    def delete_all(self) -> bool:
        """
        Delete all documents
        
        Returns:
            True if successful
        """
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM invoices")
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting all documents: {e}")
            return False
    
    def _flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
        """Flatten nested dictionary"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def _parse_amount(self, amount: Any) -> Optional[float]:
        """Parse amount string to float"""
        if amount is None:
            return None
        try:
            return float(str(amount).replace(",", "").replace("$", "").strip())
        except (ValueError, AttributeError):
            return None
