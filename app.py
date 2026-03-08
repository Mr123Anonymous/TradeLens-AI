"""
Streamlit Web Application for Trade Document Intelligence
"""
import streamlit as st
from pathlib import Path
import sys
import json
import pandas as pd

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.pipeline import DocumentPipeline
from src.data_storage import DataStorage
from src.semantic_search import SemanticSearch
from config import Config

# Page configuration
st.set_page_config(
    page_title="Trade Document Intelligence",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-box {
        padding: 1rem;
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        background-color: #d1ecf1;
        border-left: 5px solid #17a2b8;
        border-radius: 5px;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'pipeline' not in st.session_state:
    st.session_state.pipeline = None
if 'processing_complete' not in st.session_state:
    st.session_state.processing_complete = False

@st.cache_resource
def initialize_pipeline():
    """Initialize the pipeline (cached)"""
    return DocumentPipeline(use_ocr=False)

@st.cache_resource
def get_storage():
    """Get storage instance (cached)"""
    return DataStorage()

@st.cache_resource
def get_search():
    """Get search instance (cached)"""
    return SemanticSearch()

def main():
    """Main application"""
    
    # Header
    st.markdown('<div class="main-header">📄 AI-Powered Trade Document Intelligence</div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        # Navigation
        page = st.radio(
            "Navigate to:",
            ["📤 Upload & Process", "🔍 Search Documents", "📊 View All Documents", "🗑️ Manage Documents", "📈 Statistics"],
            label_visibility="collapsed"
        )
        
        st.divider()
        
        # Settings
        st.subheader("Settings")
        use_ocr = st.checkbox("Enable OCR (for scanned PDFs)", value=False)
        
        st.divider()
        
        st.caption("Built with Streamlit, Ollama, and FAISS")
    
    # Main content based on navigation
    if page == "📤 Upload & Process":
        show_upload_page()
    elif page == "🔍 Search Documents":
        show_search_page()
    elif page == "📊 View All Documents":
        show_all_documents_page()
    elif page == "🗑️ Manage Documents":
        show_manage_documents_page()
    elif page == "📈 Statistics":
        show_statistics_page()

def show_upload_page():
    """Upload and process documents page"""
    st.header("📤 Upload & Process Documents")
    
    st.markdown("""
    Upload your trade documents (invoices, bills of lading, etc.) to extract structured data automatically.
    You can upload **one or multiple PDFs at once**.
    """)
    
    # File uploader - now supports multiple files
    uploaded_files = st.file_uploader(
        "Choose PDF file(s)",
        type=['pdf'],
        accept_multiple_files=True,
        help="Upload one or multiple PDF documents"
    )
    
    if uploaded_files:
        st.info(f"Selected {len(uploaded_files)} file(s) for processing")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Show file list
            with st.expander(f"View selected files ({len(uploaded_files)})"):
                for uf in uploaded_files:
                    st.caption(f"📄 {uf.name} ({uf.size / 1024:.2f} KB)")
        
        with col2:
            process_button = st.button("🚀 Process All", type="primary", use_container_width=True)
        
        if process_button:
            # Process all files
            pipeline = initialize_pipeline()
            storage = get_storage()
            search = get_search()
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_container = st.container()
            
            successful = 0
            failed = 0
            all_results = []
            
            for idx, uploaded_file in enumerate(uploaded_files):
                # Update progress
                progress = (idx + 1) / len(uploaded_files)
                progress_bar.progress(progress)
                status_text.text(f"Processing {idx + 1} of {len(uploaded_files)}: {uploaded_file.name}")
                
                try:
                    # Save uploaded file
                    save_path = Config.UPLOADS_PATH / uploaded_file.name
                    with open(save_path, 'wb') as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Process document
                    result = pipeline.process_document(save_path)
                    all_results.append({
                        "file": uploaded_file.name,
                        "result": result
                    })
                    
                    if result["success"]:
                        successful += 1
                    else:
                        failed += 1
                
                except Exception as e:
                    failed += 1
                    all_results.append({
                        "file": uploaded_file.name,
                        "result": {
                            "success": False,
                            "errors": str(e)
                        }
                    })
            
            # Clear progress indicators
            progress_bar.empty()
            status_text.empty()
            
            # Show summary
            st.success(f"Processing complete! ✅ {successful} succeeded, ❌ {failed} failed")
            
            # Show results
            with results_container:
                for item in all_results:
                    file_name = item["file"]
                    result = item["result"]
                    
                    if result["success"]:
                        with st.expander(f" ✅ {file_name}", expanded=False):
                            extracted_data = result["extracted_data"]
                            
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric("Invoice Number", extracted_data.get("invoice_number", "N/A"))
                                st.metric("Seller", extracted_data.get("seller_name", "N/A"))
                            
                            with col2:
                                st.metric("Invoice Date", extracted_data.get("invoice_date", "N/A"))
                                st.metric("Buyer", extracted_data.get("buyer_name", "N/A"))
                            
                            with col3:
                                amount = extracted_data.get("total_amount", "N/A")
                                currency = extracted_data.get("currency", "N/A")
                                st.metric("Total Amount", f"{amount} {currency}")
                                st.metric("Pages", result.get("page_count", "N/A"))
                            
                            # Full data
                            with st.expander("View full JSON"):
                                st.json(extracted_data)
                    
                    else:
                        with st.expander(f" ❌ {file_name}", expanded=False):
                            st.error(f"Error: {result.get('errors', 'Unknown error')}")
            
            # Show results
            if result["success"]:
                st.markdown('<div class="success-box">✅ <strong>Document processed successfully!</strong></div>', unsafe_allow_html=True)
                
                # Display extracted data
                st.subheader("📋 Extracted Information")
                
                extracted_data = result["extracted_data"]
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Invoice Number", extracted_data.get("invoice_number", "N/A"))
                    st.metric("Seller", extracted_data.get("seller_name", "N/A"))
                
                with col2:
                    st.metric("Invoice Date", extracted_data.get("invoice_date", "N/A"))
                    st.metric("Buyer", extracted_data.get("buyer_name", "N/A"))
                
                with col3:
                    amount = extracted_data.get("total_amount", "N/A")
                    currency = extracted_data.get("currency", "N/A")
                    st.metric("Total Amount", f"{amount} {currency}")
                    st.metric("Pages", result.get("page_count", "N/A"))
                
                # Show full data in expandable section
                with st.expander("📄 View Full Extracted Data (JSON)"):
                    st.json(extracted_data)
                
                # Show metadata
                with st.expander("ℹ️ Processing Metadata"):
                    metadata = {
                        "Extraction Method": result.get("extraction_method", "N/A"),
                        "Text Length": f"{result.get('text_length', 0)} characters",
                        "Validation": "✓ Valid" if result["validation"]["is_valid"] else "⚠ Some fields missing"
                    }
                    st.json(metadata)
            
            else:
                st.markdown(f'<div class="error-box">❌ <strong>Processing failed:</strong><br>{result["errors"]}</div>', unsafe_allow_html=True)

def show_search_page():
    """Semantic search page"""
    st.header("🔍 Semantic Search")
    
    st.markdown("""
    Use natural language to search through your documents. Examples:
    - *"Show invoices above 50,000 USD from ABC Exports"*
    - *"Find all invoices from January 2024"*
    - *"Show high-value transactions in EUR"*
    """)
    
    # Search input
    query = st.text_input(
        "Enter your search query:",
        placeholder="e.g., invoices above 50000 USD",
        help="Use natural language to describe what you're looking for"
    )
    
    # Initialize filters dict (will be populated from expander or query)
    filters = {}
    
    # Advanced filters
    with st.expander("🔧 Advanced Filters"):
        col1, col2 = st.columns(2)
        
        with col1:
            min_amount = st.number_input("Minimum Amount", min_value=0.0, value=0.0, step=1000.0)
            seller_filter = st.text_input("Seller Name (contains)")
        
        with col2:
            max_amount = st.number_input("Maximum Amount", min_value=0.0, value=0.0, step=1000.0)
            currency_filter = st.selectbox("Currency", ["", "USD", "EUR", "GBP", "JPY", "CNY"])
        
        # Build filters dict from manual inputs
        if min_amount > 0:
            filters["min_amount"] = min_amount
        if max_amount > 0:
            filters["max_amount"] = max_amount
        if seller_filter:
            filters["seller_name"] = seller_filter
        if currency_filter:
            filters["currency"] = currency_filter
    
    # Number of results
    top_k = st.slider("Number of results", min_value=1, max_value=20, value=5)
    
    # Search button
    if st.button("🔍 Search", type="primary", use_container_width=True):
        if not query:
            st.warning("Please enter a search query")
        else:
            # Extract numeric filters from natural language query
            import re
            query_lower = query.lower()
            
            # Check for negative/exclusion queries
            exclude_currency = None
            if "not in" in query_lower or "except" in query_lower or "other than" in query_lower or "excluding" in query_lower:
                # Extract currency to exclude (e.g., "not in USD", "except EUR")
                currencies = ["USD", "EUR", "GBP", "JPY", "CNY", "AUD", "CAD", "CHF", "INR"]
                for curr in currencies:
                    if curr.lower() in query_lower:
                        exclude_currency = curr
                        break
            
            # Extract minimum amount (e.g., "above 50", "more than 50", "greater than 50")
            above_match = re.search(r'(?:above|over|more than|greater than|>|>=)\s*\$?(\d+(?:\.\d+)?)', query_lower)
            if above_match and "min_amount" not in filters:
                filters["min_amount"] = float(above_match.group(1))
            
            # Extract maximum amount (e.g., "below 100", "less than 100", "under 100")
            below_match = re.search(r'(?:below|under|less than|<|<=)\s*\$?(\d+(?:\.\d+)?)', query_lower)
            if below_match and "max_amount" not in filters:
                filters["max_amount"] = float(below_match.group(1))
            
            # Extract currency mentions (e.g., "in USD", "USD amount", "EUR invoice")
            # But skip if we're excluding currencies
            if not exclude_currency:
                currencies = ["USD", "EUR", "GBP", "JPY", "CNY", "AUD", "CAD", "CHF", "INR"]
                for curr in currencies:
                    if curr.lower() in query_lower and "currency" not in filters:
                        filters["currency"] = curr
                        break
            else:
                # Add exclude_currency to filters
                filters["exclude_currency"] = exclude_currency
            
            with st.spinner("Searching..."):
                search = get_search()
                results = search.search(query, top_k=top_k, filters=filters if filters else None)
            
            if results:
                st.success(f"Found {len(results)} matching documents")
                
                # Display results
                for i, result in enumerate(results):
                    invoice = result["invoice"]
                    score = result["score"]
                    
                    with st.container():
                        st.markdown(f"### Result {i+1} (Similarity: {score:.3f})")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.write("**Invoice #:**", invoice.get("invoice_number", "N/A"))
                        with col2:
                            st.write("**Date:**", invoice.get("invoice_date", "N/A"))
                        with col3:
                            amount = invoice.get("total_amount", "N/A")
                            currency = invoice.get("currency", "N/A")
                            st.write("**Amount:**", f"{amount} {currency}")
                        with col4:
                            st.write("**Seller:**", invoice.get("seller_name", "N/A"))
                        
                        with st.expander("View Details"):
                            st.json(invoice)
                        
                        st.divider()
            else:
                st.info("No matching documents found. Try adjusting your search query or filters.")

def show_all_documents_page():
    """View all documents page"""
    st.header("📊 All Documents")
    
    storage = get_storage()
    
    # Load all documents
    with st.spinner("Loading documents..."):
        documents = storage.load_all(format="db")
    
    if documents:
        st.success(f"Total documents: {len(documents)}")
        
        # Convert to DataFrame
        df = pd.DataFrame(documents)
        
        # Select columns to display
        display_columns = [
            "invoice_number", "invoice_date", "seller_name", 
            "buyer_name", "total_amount", "currency", "extracted_at"
        ]
        
        # Filter columns that exist
        display_columns = [col for col in display_columns if col in df.columns]
        
        # Display DataFrame
        st.dataframe(
            df[display_columns],
            use_container_width=True,
            hide_index=True
        )
        
        # Download as CSV
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name="invoices.csv",
            mime="text/csv"
        )
        
        # Summary statistics
        st.subheader("📈 Summary Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Documents", len(documents))
        
        with col2:
            if "total_amount" in df.columns:
                total_value = df["total_amount"].sum()
                st.metric("Total Value", f"${total_value:,.2f}")
        
        with col3:
            if "currency" in df.columns:
                currencies = df["currency"].nunique()
                st.metric("Currencies", currencies)
        
        with col4:
            if "seller_name" in df.columns:
                sellers = df["seller_name"].nunique()
                st.metric("Unique Sellers", sellers)
    
    else:
        st.info("No documents found. Upload and process some documents first!")

def show_manage_documents_page():
    """Manage documents - view and delete"""
    st.header("🗑️ Manage Documents")
    
    st.markdown("""
    View and delete uploaded documents. Deleting a document will:
    - Remove it from the database
    - Remove it from the search index
    - Delete the uploaded PDF file
    """)
    
    storage = get_storage()
    search = get_search()
    
    # Load all documents
    documents = storage.load_all(format="db")
    
    if documents:
        st.info(f"Total documents: {len(documents)}")
        
        # Selection mode
        st.subheader("Select Documents to Delete")
        
        # Create a DataFrame for selection
        df = pd.DataFrame(documents)
        
        # Add a checkbox column for selection
        selected_docs = []
        
        # Show each document with a checkbox
        for idx, doc in enumerate(documents):
            col1, col2, col3, col4, col5 = st.columns([0.5, 2, 2, 2, 2])
            
            with col1:
                if st.checkbox("", key=f"del_{idx}"):
                    selected_docs.append(doc)
            
            with col2:
                st.write(f"**{doc.get('invoice_number', 'N/A')}**")
            
            with col3:
                st.write(doc.get('invoice_date', 'N/A'))
            
            with col4:
                st.write(doc.get('seller_name', 'N/A'))
            
            with col5:
                amount = doc.get('total_amount', 'N/A')
                currency = doc.get('currency', 'N/A')
                st.write(f"{amount} {currency}")
        
        st.divider()
        
        # Bulk actions
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.write(f"**{len(selected_docs)} document(s) selected**")
        
        with col2:
            if st.button("Select All", use_container_width=True):
                st.rerun()
        
        with col3:
            if len(selected_docs) > 0:
                if st.button(f"🗑️ Delete {len(selected_docs)} Selected", type="primary", use_container_width=True):
                    with st.spinner(f"Deleting {len(selected_docs)} documents..."):
                        deleted = 0
                        for doc in selected_docs:
                            try:
                                # Delete from database
                                if 'id' in doc:
                                    if storage.delete_by_id(doc['id']):
                                        deleted += 1
                                
                                # Delete uploaded PDF if it exists
                                if 'file_name' in doc:
                                    pdf_path = Config.UPLOADS_PATH / doc['file_name']
                                    if pdf_path.exists():
                                        pdf_path.unlink()
                                
                            except Exception as e:
                                st.error(f"Failed to delete {doc.get('invoice_number', 'unknown')}: {str(e)}")
                        
                        # Rebuild search index without deleted documents
                        if deleted > 0:
                            st.info("Rebuilding search index...")
                            remaining_docs = storage.load_all(format="db")
                            search.clear_index()
                            search.add_documents(remaining_docs)
                            search.save_index()
                        
                        st.success(f"Successfully deleted {deleted} document(s)!")
                        st.rerun()
        
        # Danger zone
        st.divider()
        with st.expander("⚠️ Danger Zone", expanded=False):
            st.warning("**Delete ALL Documents**")
            st.write("This will permanently delete all documents, search index, and uploaded files.")
            
            confirm = st.text_input("Type 'DELETE ALL' to confirm:")
            
            if st.button("🗑️ Delete All Documents", type="secondary"):
                if confirm == "DELETE ALL":
                    with st.spinner("Deleting all documents..."):
                        # Clear database
                        storage.delete_all()
                        
                        # Clear search index
                        search.clear_index()
                        search.save_index()
                        
                        # Delete all uploaded files
                        for pdf_file in Config.UPLOADS_PATH.glob("*.pdf"):
                            pdf_file.unlink()
                        
                        st.success("All documents deleted!")
                        st.rerun()
                else:
                    st.error("Please type 'DELETE ALL' to confirm")
    
    else:
        st.info("No documents found. Upload and process some documents first!")

def show_statistics_page():
    """Statistics and analytics page"""
    st.header("📈 Statistics & Analytics")
    
    storage = get_storage()
    search = get_search()
    
    # Load documents
    documents = storage.load_all(format="db")
    
    if documents:
        df = pd.DataFrame(documents)
        
        # Overview
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Documents", len(documents))
        
        with col2:
            if "total_amount" in df.columns:
                avg_amount = df["total_amount"].mean()
                st.metric("Avg Amount", f"${avg_amount:,.2f}")
        
        with col3:
            if "seller_name" in df.columns:
                sellers = df["seller_name"].nunique()
                st.metric("Unique Sellers", sellers)
        
        with col4:
            if "buyer_name" in df.columns:
                buyers = df["buyer_name"].nunique()
                st.metric("Unique Buyers", buyers)
        
        st.divider()
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Currency Distribution")
            if "currency" in df.columns:
                currency_counts = df["currency"].value_counts()
                st.bar_chart(currency_counts)
        
        with col2:
            st.subheader("Top Sellers by Transaction Count")
            if "seller_name" in df.columns:
                seller_counts = df["seller_name"].value_counts().head(10)
                st.bar_chart(seller_counts)
        
        # Search index stats
        st.divider()
        st.subheader("🔍 Search Index Statistics")
        
        stats = search.get_statistics()
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Indexed Documents", stats["total_documents"])
        with col2:
            st.metric("Embedding Model", stats["model_name"])
        with col3:
            st.metric("Embedding Dimension", stats["embedding_dimension"])
        
        # Rebuild index button
        if st.button("🔄 Rebuild Search Index", help="Rebuild the semantic search index from the database"):
            with st.spinner("Rebuilding index..."):
                pipeline = initialize_pipeline()
                pipeline.rebuild_search_index()
            st.success("Search index rebuilt successfully!")
    
    else:
        st.info("No data available. Upload and process some documents first!")

if __name__ == "__main__":
    main()
