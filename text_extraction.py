import re
import pandas as pd
from typing import Dict, List, Tuple, Optional

def extract_cas_numbers(text: str) -> List[str]:
    """
    Extract CAS numbers from text.
    
    Args:
        text: Text to search for CAS numbers
        
    Returns:
        List of found CAS numbers
    """
    # Improved patterns to capture more CAS number formats
    cas_patterns = [
        r'\b(\d{1,7}-\d{2}-\d{1})\b',  # Standard format
        r'CAS(?:[\s-]*No\.?|[-\s]*Number)[:\s]*(\d{1,7}-\d{2}-\d{1})',  # With prefix
        r'CAS[:\s]*(\d{1,7}-\d{2}-\d{1})',  # Simple CAS prefix
        r'(?:CAS|CASNO|CAS-No)[^a-zA-Z0-9]*(\d{1,7}-\d{2}-\d{1})'  # Different variations
    ]
    
    matches = []
    for pattern in cas_patterns:
        found = re.findall(pattern, text)
        matches.extend(found)
    
    # Remove duplicates while preserving order
    unique_matches = []
    seen = set()
    for cas in matches:
        if cas not in seen:
            seen.add(cas)
            unique_matches.append(cas)
    
    return unique_matches

def extract_hazard_statements(text: str) -> List[Tuple[str, str]]:
    """
    Extract H statements (hazard statements) from text.
    
    Args:
        text: Text to search for hazard statements
        
    Returns:
        List of tuples containing (code, statement)
    """
    # Look for patterns like H200, H201, etc. followed by their description
    h_pattern = r'(H\d{3}(?:[+]\d{3})*)[:\s]+([^\n]+)'
    
    h_statements = re.findall(h_pattern, text, re.IGNORECASE)
    return h_statements

def extract_precautionary_statements(text: str) -> List[Tuple[str, str]]:
    """
    Extract P statements (precautionary statements) from text.
    
    Args:
        text: Text to search for precautionary statements
        
    Returns:
        List of tuples containing (code, statement)
    """
    # Look for patterns like P200, P201, etc. followed by their description
    p_pattern = r'(P\d{3}(?:[+]\d{3})*)[:\s]+([^\n]+)'
    
    p_statements = re.findall(p_pattern, text, re.IGNORECASE)
    return p_statements

def extract_section(text: str, section_num: int) -> Optional[str]:
    """
    Extract a specific section from an SDS document by its number.
    
    Args:
        text: The complete text of the SDS document
        section_num: The section number to extract
        
    Returns:
        The text of the specified section, or None if not found
    """
    # Pattern to match section headers like "SECTION 1:", "1.", "Section 1", etc.
    section_start_pattern = r'(?:SECTION\s+|^)' + str(section_num) + r'(?:[:\.]\s*|\s+)([^\n]+)(?:\n)'
    next_section_pattern = r'(?:SECTION\s+|^)' + str(section_num + 1) + r'(?:[:\.]\s*|\s+)'
    
    # Find the start of the requested section
    section_start = re.search(section_start_pattern, text, re.IGNORECASE | re.MULTILINE)
    if not section_start:
        return None
    
    start_pos = section_start.end()
    
    # Find the start of the next section
    next_section = re.search(next_section_pattern, text[start_pos:], re.IGNORECASE | re.MULTILINE)
    
    if next_section:
        # Extract text from end of section heading to start of next section
        section_text = text[start_pos:start_pos + next_section.start()].strip()
    else:
        # If no next section is found, take the rest of the text
        section_text = text[start_pos:].strip()
    
    return section_text

def find_product_name(text: str) -> Optional[str]:
    """
    Find the product name in the SDS document.
    
    Args:
        text: The complete text of the SDS document
        
    Returns:
        The product name if found, None otherwise
    """
    patterns = [
        r'Product\s+name\s*[:\n](.*?)(?:\n\s*[A-Z]|\n\n)',
        r'Product\s+identifier\s*[:\n](.*?)(?:\n\s*[A-Z]|\n\n)',
        r'Name\s+[:\n](.*?)(?:\n\s*[A-Z]|\n\n)',
        r'\bname[:\s]+(.*?)(?:\n|$)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
    
    return None

def find_supplier_info(text: str) -> Optional[str]:
    """
    Find supplier information in the SDS document.
    
    Args:
        text: The complete text of the SDS document
        
    Returns:
        The supplier information if found, None otherwise
    """
    # Extract section 1 which usually contains supplier info
    section1 = extract_section(text, 1)
    if not section1:
        return None
    
    patterns = [
        r'(?:Supplier|Manufacturer|Company)[:\s]+(.*?)(?:\n\s*[A-Z]|\n\n|Emergency)',
        r'Details of the supplier[:\s]+(.*?)(?:\n\s*[A-Z]|\n\n|Emergency)',
        r'Supplier\s+details[:\s]+(.*?)(?:\n\s*[A-Z]|\n\n|Emergency)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, section1, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
    
    # Look for address and phone
    address_match = re.search(r'Address[:\s]+(.*?)(?:\n|$)', section1, re.IGNORECASE)
    phone_match = re.search(r'(?:Phone|Tel)[:\s]+(.*?)(?:\n|$)', section1, re.IGNORECASE)
    
    if address_match or phone_match:
        parts = []
        if address_match:
            parts.append(address_match.group(1).strip())
        if phone_match:
            parts.append(f"Phone: {phone_match.group(1).strip()}")
        
        return ', '.join(parts)
    
    return None
