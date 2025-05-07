import fitz  # PyMuPDF
import base64
from io import BytesIO
import tempfile
import os
import pandas as pd
import json

# Constants
DATA_DIR = "data"
REGISTER_FILE = os.path.join(DATA_DIR, "sds_register.csv")
HISTORY_FILE = os.path.join(DATA_DIR, "extraction_history.json")

def read_pdf_text(pdf_path: str) -> str:
    """
    Extract text from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text as a string
    """
    # Open the PDF
    doc = fitz.open(pdf_path)
    
    # Extract text from all pages
    full_text = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        full_text.append(text)
    
    # Close the document
    doc.close()
    
    # Join text from all pages
    return "\n".join(full_text)

def display_pdf(pdf_file) -> str:
    """
    Display a PDF file in Streamlit.
    
    Args:
        pdf_file: Streamlit UploadedFile object
        
    Returns:
        HTML for displaying the PDF
    """
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_file.getvalue())
        pdf_path = tmp.name
    
    # Open the PDF
    doc = fitz.open(pdf_path)
    
    # Get the first page as an image for preview
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
    
    # Convert to image data
    img_data = pix.tobytes("png")
    
    # Clean up
    doc.close()
    os.unlink(pdf_path)
    
    # Create the HTML for display
    image_html = f"""
    <div style="display: flex; justify-content: center;">
        <img src="data:image/png;base64,{base64.b64encode(img_data).decode()}" 
             style="max-width: 100%; max-height: 500px; object-fit: contain;" />
    </div>
    <p style="text-align: center; font-style: italic;">PDF Preview (first page only)</p>
    """
    
    return image_html

def get_file_size(file) -> str:
    """
    Get human-readable file size.
    
    Args:
        file: Streamlit UploadedFile object
        
    Returns:
        Formatted file size string
    """
    size_bytes = len(file.getvalue())
    
    # Format size
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    
    return f"{size_bytes:.2f} TB"

def normalize_text(text: str) -> str:
    """
    Normalize text by removing extra whitespace and line breaks.
    
    Args:
        text: Input text
        
    Returns:
        Normalized text
    """
    # Replace multiple spaces with a single space
    text = ' '.join(text.split())
    
    return text

def save_dataframe(df: pd.DataFrame, history: list = None) -> tuple:
    """
    Save the dataframe to the SQLite database.
    
    Args:
        df: The dataframe to save
        history: The extraction history to save
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Import the database handler functions
        from db_handler import save_to_database
        
        # Save both dataframe and history to SQLite database
        success, message = save_to_database(df, history)
        
        # Also save to CSV as backup
        # Create the data directory if it doesn't exist
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        
        # Save the dataframe to CSV as backup
        df.to_csv(REGISTER_FILE, index=False)
        
        return success, message
    except Exception as e:
        error_message = f"Error saving data: {e}"
        print(error_message)
        return False, error_message

def load_dataframe() -> tuple:
    """
    Load the dataframe from the SQLite database.
    
    Returns:
        Tuple of (dataframe, history)
    """
    try:
        # Import the database handler functions
        from db_handler import load_from_database
        
        # Load from SQLite database
        df, history = load_from_database()
        
        # If database load fails, try falling back to CSV/JSON files
        if df is None:
            print("Database load failed, trying CSV/JSON fallback...")
            df = None
            history = []
            
            # Load the dataframe if the file exists
            if os.path.exists(REGISTER_FILE):
                df = pd.read_csv(REGISTER_FILE)
            
            # Load the extraction history if the file exists
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r') as f:
                    history = json.load(f)
                    
            # If we successfully loaded from CSV/JSON, try to save to the database
            if df is not None:
                from db_handler import save_to_database
                save_to_database(df, history)
                print("Migrated data from CSV/JSON to SQLite database")
                
        return df, history
    except Exception as e:
        print(f"Error loading data: {e}")
        # Fallback to CSV/JSON if there's an error
        df = None
        history = []
        
        try:
            # Load the dataframe if the file exists
            if os.path.exists(REGISTER_FILE):
                df = pd.read_csv(REGISTER_FILE)
            
            # Load the extraction history if the file exists
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r') as f:
                    history = json.load(f)
        except Exception as load_error:
            print(f"Fallback loading error: {load_error}")
        
        return df, history
