import sys
import fitz
import re
from pprint import pprint


def extract_sds_sections(pdf_path):
    """Extract all sections from an SDS document by their section numbers."""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    
    # Pattern to find all sections by their headers (SECTION X:)
    section_pattern = r'SECTION\s+(\d+)[:\.\s]+([^\n]+)(?:\n)(.*?)(?=(?:SECTION\s+\d+)|$)'
    sections = {}
    
    for match in re.finditer(section_pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE):
        section_num = match.group(1)
        section_title = match.group(2).strip()
        section_content = match.group(3).strip()
        
        sections[section_num] = {
            'title': section_title,
            'content': section_content[:500]  # Limit content to 500 chars for readability
        }
    
    return sections


def extract_hazard_data(pdf_path):
    """Focus on extracting hazard statements, classifications, and health categories."""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    
    result = {
        'product_name': '',
        'supplier': '',
        'cas_number': '',
        'hazards': '',
        'hazard_statements': [],
        'precautionary_statements': [],
        'flash_point': '',
        'health_category': '',
        'physical_hazard': ''
    }
    
    # Extract product name
    product_name_match = re.search(r'Product name\s*[:\n](.*?)(?:\n\s*[A-Z]|\n\n)', text, re.IGNORECASE | re.DOTALL)
    if product_name_match:
        result['product_name'] = product_name_match.group(1).strip()
    
    # Extract supplier
    supplier_match = re.search(r'(?:Supplier|Company)[:\s]+(.*?)(?:\n\s*[A-Z]|\n\n|Emergency)', text, re.IGNORECASE | re.DOTALL)
    if supplier_match:
        result['supplier'] = supplier_match.group(1).strip()
    
    # Extract CAS number
    cas_match = re.search(r'CAS(?:[\s-]*No\.?|[-\s]*Number)[:\s]*([\d\-]+)', text, re.IGNORECASE)
    if cas_match:
        result['cas_number'] = cas_match.group(1).strip()
    
    # Extract hazard statements (H codes)
    h_statements = re.findall(r'(H\d{3}[^:,;\n]*?)[,;\n]', text)
    if h_statements:
        result['hazard_statements'] = list(set(h_statements))  # Deduplicate
    
    # Extract precautionary statements (P codes)
    p_statements = re.findall(r'(P\d{3}[^:,;\n]*?)[,;\n]', text)
    if p_statements:
        result['precautionary_statements'] = list(set(p_statements))  # Deduplicate
    
    # Extract flash point
    flash_point_match = re.search(r'Flash[- ]?point[^:]*?:\s*([^,\n]*)', text, re.IGNORECASE)
    if flash_point_match:
        result['flash_point'] = flash_point_match.group(1).strip()
    
    # Extract health category
    health_cat_match = re.search(r'(?:skin|eye|repro|reproductive|toxicity|respir)[^,\n]*?(?:category|cat\.?)\s*(\d[A-Z]?)', text, re.IGNORECASE)
    if health_cat_match:
        result['health_category'] = health_cat_match.group(1).strip()
    
    # Extract hazard classification - look for Section 2
    section_2_match = re.search(r'SECTION\s+2[:\.\s]+([^\n]+)(?:\n)(.*?)(?=SECTION\s+3)', text, re.IGNORECASE | re.DOTALL)
    if section_2_match:
        section_2_title = section_2_match.group(1).strip()
        section_2_content = section_2_match.group(2).strip()
        result['hazards'] = section_2_content[:500]  # Take first 500 chars
    
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python inspect_sds.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    print(f"\n\nEXAMINING SDS DOCUMENT: {pdf_path}\n")
    
    print("EXTRACTING SECTION DATA:")
    sections = extract_sds_sections(pdf_path)
    for section_num, section_data in sorted(sections.items(), key=lambda x: int(x[0])):
        print(f"\nSECTION {section_num}: {section_data['title']}")
        print("-" * 80)
        print(f"{section_data['content'][:300]}...")
    
    print("\n\nEXTRACTING HAZARD DATA:")
    hazard_data = extract_hazard_data(pdf_path)
    pprint(hazard_data)