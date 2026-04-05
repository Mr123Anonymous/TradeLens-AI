# 📄 AI-Powered Trade Document Intelligence System

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

An intelligent system for extracting, storing, and searching trade documents (invoices, bills of lading, etc.) using AI and semantic search.

## 🎯 Overview

This system automates the extraction of structured data from trade documents and enables intelligent search using embeddings. It mirrors real-world trade finance workflows by:

- **Extracting text** from PDF documents (digital and scanned)
- **Using LLMs** to extract structured fields (invoice number, dates, amounts, etc.)
- **Storing data** in multiple formats (JSON, CSV, SQLite)
- **Enabling semantic search** using embeddings and vector databases

## 🏗️ Architecture

```
┌─────────────────┐
│  PDF Document   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ PDF Extraction  │  ← PyMuPDF / pdfplumber / OCR
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ LLM Extraction  │  ← Ollama (Local LLMs)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Data Storage   │  ← JSON / CSV / SQLite
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Vector Embedding│  ← Sentence Transformers
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ FAISS Index     │  ← Semantic Search
└─────────────────┘
```

## ✨ Features

### 1. **Multi-Method PDF Extraction**
- **PyMuPDF** for fast digital PDF extraction
- **pdfplumber** for better table handling
- **OCR (pytesseract)** for scanned documents
- Automatic fallback between methods

### 2. **LLM-Powered Data Extraction**
- Structured field extraction using local LLMs via Ollama
- Extracts:
  - Invoice Number
  - Invoice Date
  - Seller Name
  - Buyer Name
  - Total Amount
  - Currency

### 3. **Flexible Data Storage**
- **JSON** - Human-readable format
- **CSV** - Spreadsheet compatible
- **SQLite** - Queryable database
- Automatic deduplication

### 4. **Semantic Search**
- Natural language queries
- Sentence embeddings (all-MiniLM-L6-v2)
- FAISS vector database
- Advanced filtering by amount, currency, seller, etc.

### 5. **Web Interface**
- Streamlit-based UI
- Document upload & processing
- Real-time search
- Data visualization & analytics

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- Ollama installed and running (free, local LLM)
- For OCR: Tesseract-OCR installed

### Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd TradeLens
```

2. **Create virtual environment**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
# Copy example env file
copy .env.example .env

# Edit .env if you need to customize Ollama settings
```

### Running the Application

#### Option 1: Streamlit Web Interface (Recommended)
```bash
streamlit run app.py --server.fileWatcherType none
```

Then open your browser to `http://localhost:8501`

#### Option 2: Command Line
```python
from pathlib import Path
from src.pipeline import DocumentPipeline

# Initialize pipeline
pipeline = DocumentPipeline(use_ocr=False)

# Process single document
result = pipeline.process_document(Path("your_invoice.pdf"))

# Process entire directory
results = pipeline.process_directory(Path("./invoices"))

# Search documents
from src.semantic_search import SemanticSearch
search = SemanticSearch()
results = search.search("invoices above 50000 USD from ABC Exports")
for result in results:
    print(result["invoice"])
```

## 📦 Project Structure

```
DocInt/
├── src/
│   ├── pdf_extractor.py      # PDF text extraction
│   ├── llm_extractor.py      # LLM-based field extraction
│   ├── data_storage.py       # Data persistence (JSON/CSV/DB)
│   ├── semantic_search.py    # Embedding & vector search
│   └── pipeline.py           # Main orchestration pipeline
├── app.py                    # Streamlit web interface
├── config.py                 # Configuration management
├── requirements.txt          # Python dependencies
├── .env.example             # Environment variables template
├── .gitignore               # Git ignore rules
└── README.md                # This file

Generated directories:
├── data/                    # Stored invoices (JSON/CSV/DB)
├── vector_db/              # FAISS index & embeddings
└── uploads/                # Uploaded PDF files
```

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **PDF Processing** | PyMuPDF, pdfplumber, pytesseract |
| **LLM** | Ollama (free, local) |
| **Embeddings** | sentence-transformers |
| **Vector DB** | FAISS |
| **Storage** | SQLite, JSON, CSV |
| **Web Framework** | Streamlit |
| **Data Processing** | Pandas, NumPy |

## 🔍 Usage Examples

### 1. Upload and Process Document
```python
from src.pipeline import DocumentPipeline

pipeline = DocumentPipeline()
result = pipeline.process_document(Path("invoice.pdf"))

if result["success"]:
    print(result["extracted_data"])
```

### 2. Semantic Search
```python
from src.semantic_search import SemanticSearch

search = SemanticSearch()

# Natural language query
results = search.search(
    "Show invoices above 50,000 USD from ABC Exports",
    top_k=5
)

# With filters
results = search.search(
    "high-value European invoices",
    top_k=10,
    filters={"min_amount": 100000, "currency": "EUR"}
)
```

### 3. Query Database
```python
from src.data_storage import DataStorage

storage = DataStorage()

# Get all invoices
all_invoices = storage.load_all(format="db")

# Search with criteria
results = storage.search({
    "seller_name": "ABC Exports",
    "min_amount": 50000,
    "currency": "USD"
})
```

## 🧪 Testing

Sample invoice for testing:

```
INVOICE
Invoice No: INV-2024-001
Date: January 15, 2024

From: ABC Exports Ltd.
123 Trade Street
New York, NY 10001

To: XYZ Imports Inc.
456 Commerce Ave
Los Angeles, CA 90001

Items:
- Product A: $25,000
- Product B: $27,500

Total Amount: $52,500.00 USD
```

Save this as a PDF and upload through the Streamlit interface or process via CLI.

## 🎯 Key Concepts Demonstrated

### 1. **Prompt Engineering**
- Structured prompts for consistent LLM outputs
- JSON-formatted responses
- Field validation and error handling

### 2. **Vector Embeddings**
- Converting text to numerical vectors
- Similarity search using cosine distance
- Hybrid search (semantic + filters)

### 3. **Data Pipeline**
- ETL (Extract, Transform, Load) workflow
- Error handling and fallback strategies
- Multi-format data persistence

### 4. **Real-World ML Application**
- Practical trade finance use case
- Production-ready architecture
- Scalable design patterns

## 🚀 Future Improvements

- [ ] **Multi-language support** (extract from invoices in different languages)
- [ ] **Table extraction** (line items from invoice tables)
- [ ] **Document classification** (invoice vs. bill of lading vs. other)
- [ ] **Duplicate detection** (find duplicate invoices)
- [ ] **Batch processing** (async document processing)
- [ ] **Advanced analytics** (spending patterns, supplier analysis)
- [ ] **Export formats** (Excel, PDF reports)
- [ ] **User authentication** (multi-user support)
- [ ] **Cloud deployment** (Docker, AWS/Azure)

## 📊 Performance

| Task | Time |
|------|------|
| PDF Extraction (1 page) | ~0.5s |
| LLM Extraction (Ollama) | ~5-10s |
| Vector Embedding | ~0.1s |
| Search Query | ~0.05s |

## 🔒 Security Notes

- **API Keys**: Never commit `.env` file to version control
- **Data Privacy**: Sensitive documents are stored locally
- **Ollama**: 100% local processing, no external API calls

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Ollama** for local LLM models
- **Sentence Transformers** for embedding models
- **FAISS** by Facebook AI for vector search
- **Streamlit** for the amazing web framework

## 📞 Support

For questions or issues, please open an issue on GitHub or contact [sohanneogi@gmail.com]

---

**Built with ❤️ for the trade finance community**

---

### Quick Command Reference

```bash
# Install dependencies
pip install -r requirements.txt

# Run Streamlit app
streamlit run app.py

# Install Tesseract (Windows)
# Download from: https://github.com/UB-Mannheim/tesseract/wiki

# Install Ollama (for local LLM)
# Download from: https://ollama.ai
ollama pull mistral
```

---

**⭐ If you find this project helpful, please star the repository!**
