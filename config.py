"""
Configuration management for the Trade Document Intelligence System
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""
    
    # API Keys
    USE_OLLAMA = os.getenv("USE_OLLAMA", "false").lower() == "true"
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    # Paths
    BASE_DIR = Path(__file__).parent
    DATA_STORAGE_PATH = Path(os.getenv("DATA_STORAGE_PATH", "./data"))
    VECTOR_DB_PATH = Path(os.getenv("VECTOR_DB_PATH", "./vector_db"))
    UPLOADS_PATH = BASE_DIR / "uploads"
    
    # Model Configuration
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    
    # Create directories if they don't exist
    @classmethod
    def setup_directories(cls):
        """Create necessary directories"""
        cls.DATA_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
        cls.VECTOR_DB_PATH.mkdir(parents=True, exist_ok=True)
        cls.UPLOADS_PATH.mkdir(parents=True, exist_ok=True)
    
    # Extraction Fields
    EXTRACTION_FIELDS = [
        "invoice_number",
        "invoice_date",
        "seller_name",
        "buyer_name",
        "total_amount",
        "currency"
    ]

# Initialize directories
Config.setup_directories()
