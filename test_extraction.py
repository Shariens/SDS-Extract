import fitz  # PyMuPDF
import os
import re
import sys
from pprint import pprint
import argparse
sys.path.append('.')  # Add current directory to path
from sds_extractor import extract_sds_data
from utils import read_pdf_text
from inspect_sds import extract_hazard_data

def extract_text(pdf_path):
    print(f"Attempting to extract text from: {pdf_path}")
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

def debug_extraction(pdf_path):
    # Extract text from PDF
    text = extract_text(pdf_path)
    print(f"Extracted {len(text)} characters of text")
    
    # Test each extraction method
    print("\nTESTING PATTERN-BASED EXTRACTION:")
    pattern_data = extract_sds_data(text, "Pattern-based")
    for key, value in sorted(pattern_data.items()):
        if isinstance(value, str):
            display_value = value[:100] + "..." if len(value) > 100 else value
            print(f"{key}: {display_value}")
        else:
            print(f"{key}: {value}")
        
    print("\nTESTING SECTION-BASED EXTRACTION:")
    section_data = extract_sds_data(text, "Section-based") 
    for key, value in sorted(section_data.items()):
        if isinstance(value, str):
            display_value = value[:100] + "..." if len(value) > 100 else value
            print(f"{key}: {display_value}")
        else:
            print(f"{key}: {value}")
        
    print("\nTESTING AUTOMATIC EXTRACTION:")
    data = extract_sds_data(text, "Automatic")
    for key, value in sorted(data.items()):
        if isinstance(value, str):
            display_value = value[:100] + "..." if len(value) > 100 else value
            print(f"{key}: {display_value}")
        else:
            print(f"{key}: {value}")
    
    # Extract some specific patterns for debugging
    print("\nTESTING SPECIFIC PATTERNS:")
    
    # Product Name
    print("\nProduct Name patterns:")
    product_patterns = [
        r'Product\s+name\s*[:\n](.*?)(?:\n\s*[A-Z]|\n\n)',
        r'Product\s+identifier\s*[:\n](.*?)(?:\n\s*[A-Z]|\n\n)',
        r'Name\s+[:\n](.*?)(?:\n\s*[A-Z]|\n\n)',
        r'(?:SECTION\s+1)[^,]*?[Pp]roduct[^:]*?:\s*(.*?)(?:\n\s*[A-Z]|\n\n)',
    ]
    for pattern in product_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            print(f"Match: {match.group(1).strip()}")
        else:
            print(f"No match for pattern: {pattern}")
    
    # CAS Number
    print("\nCAS Number patterns:")
    cas_patterns = [
        r'CAS(?:[\s-]*No\.?|[-\s]*Number)[:\s]*([\d\-]+)',
        r'CAS[:\s]*([\d\-]+)',
        r'(?:CAS|CASNO|CAS-No)[^a-zA-Z0-9]*(\d{1,7}-\d{2}-\d{1})',
        r'(?:\D|^)(\d{1,7}-\d{2}-\d{1})(?:\D|$)'
    ]
    for pattern in cas_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            print(f"Match: {match.group(1).strip()}")
        else:
            print(f"No match for pattern: {pattern}")
    
    # Hazard Classification
    print("\nHazard Classification patterns:")
    hazard_patterns = [
        r'Hazard(?:\s+Classification|\s+class)[:\s]+(.*?)(?:\n\s*[A-Z]|\n\n|Precautionary)',
        r'Classification[:\s]+(.*?)(?:\n\s*[A-Z]|\n\n)',
        r'Classification according to[^:]*?:[^:]*?(.*?)(?:\n\s*[A-Z]|\n\n)',
    ]
    for pattern in hazard_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            print(f"Match: {match.group(1).strip()}")
        else:
            print(f"No match for pattern: {pattern}")
    
    # Supplier Information
    print("\nSupplier Information patterns:")
    supplier_patterns = [
        r'Company\s*:\s*([^\n]+)', 
        r'Details of the supplier[^:]*?:\s*([^\n]+)',
        r'(?:SECTION\s+1|1\.)[^A-Z]*?Company\s*:\s*([^\n]+)',
        r'Manufacturer\s*:\s*([^\n]+)',
        r'Supplier\s*:\s*([^\n]+)',
    ]
    for pattern in supplier_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            print(f"Match: {match.group(1).strip()}")
        else:
            print(f"No match for pattern: {pattern}")
    
    # Health Category
    print("\nHealth Category patterns:")
    health_category_patterns = [
        r'[Ss]kin\s+(?:irritation|corrosion|sensitization)[^,\n]*?[(\s](?:Category|Cat\.?)[)\s]*(\d[A-Z]?)',
        r'[Ee]ye\s+(?:irritation|damage)[^,\n]*?[(\s](?:Category|Cat\.?)[)\s]*(\d[A-Z]?)',
        r'[Ee]ye\s+[Ii]rrit\.\s*(\d+[A-Z]?)',
        r'[Ss]kin\s+[Ii]rrit\.\s*(\d+[A-Z]?)',
    ]
    for pattern in health_category_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            print(f"Match: {match.group(1).strip()}")
        else:
            print(f"No match for pattern: {pattern}")
    
    # Try the comprehensive hazard data extraction
    print("\nComprehensive Hazard Data Extraction:")
    hazard_data = extract_hazard_data(pdf_path)
    for key, value in hazard_data.items():
        if isinstance(value, str):
            display_value = value[:100] + "..." if len(value) > 100 else value
            print(f"{key}: {display_value}")
        else:
            print(f"{key}: {value}")
    
    return data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test SDS extraction on PDF files')
    parser.add_argument('pdf_path', type=str, nargs='?', default='attached_assets/1_ 1-Methyl-2-pyrrolidone EMPLURA®.pdf',
                        help='Path to the PDF file to test')
    
    args = parser.parse_args()
    pdf_path = args.pdf_path
    
    if os.path.exists(pdf_path):
        print(f"Testing extraction on {os.path.basename(pdf_path)}")
        data = debug_extraction(pdf_path)
    else:
        print(f"File not found: {pdf_path}")