import pytesseract
from PIL import Image
import fitz  # PyMuPDF
import tempfile
import os
import io
import numpy as np

def is_scanned_pdf(pdf_path: str) -> bool:
    """
    Determine if a PDF is likely scanned (image-based) vs. digitally created.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Boolean indicating if the PDF is likely scanned
    """
    # Open the PDF
    doc = fitz.open(pdf_path)
    
    # Check first few pages (up to 3)
    num_pages_to_check = min(3, len(doc))
    text_count = 0
    image_count = 0
    
    for page_num in range(num_pages_to_check):
        page = doc[page_num]
        
        # Count text
        text = page.get_text()
        text_count += len(text)
        
        # Count images
        image_list = page.get_images(full=True)
        image_count += len(image_list)
    
    doc.close()
    
    # Heuristic: if the PDF has very little text but has images, it's likely scanned
    if text_count < 500 and image_count > 0:
        return True
    # Or if it has some text but a high ratio of images to text
    elif text_count > 0 and image_count > 0 and (image_count / text_count) > 0.01:
        return True
    
    return False

def process_ocr(pdf_path: str) -> str:
    """
    Process a PDF using OCR to extract text.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text from the PDF
    """
    # Open the PDF
    doc = fitz.open(pdf_path)
    full_text = []
    
    # Process each page
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # First try to get text directly
        text = page.get_text()
        
        # If little or no text, use OCR
        if len(text.strip()) < 50:
            # Get the page as a pixmap
            pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
            
            # Save as a temporary image file
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                pix.save(temp_file.name)
                temp_path = temp_file.name
            
            # Perform OCR on the image
            img = Image.open(temp_path)
            ocr_text = pytesseract.image_to_string(img)
            
            # Clean up the temporary file
            os.unlink(temp_path)
            
            # Add the OCR text
            full_text.append(ocr_text)
        else:
            # Use the text we already extracted
            full_text.append(text)
    
    doc.close()
    
    return "\n".join(full_text)
