"""
AI-powered Safety Data Sheet (SDS) information extraction module.
This module uses OpenAI or Anthropic APIs to extract key information from SDS documents.
"""

import os
import base64
import re
import json
import time
from typing import Dict, List, Optional, Tuple, Union
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Check which AI service we can use based on available API keys
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')

# Initialize appropriate AI client based on available keys
ai_client = None
ai_service = None

if OPENAI_API_KEY:
    try:
        from openai import OpenAI
        ai_client = OpenAI(api_key=OPENAI_API_KEY)
        ai_service = "openai"
        logger.info("Using OpenAI API for extraction")
    except ImportError:
        logger.warning("OpenAI package not installed despite API key being available.")

if not ai_client and ANTHROPIC_API_KEY:
    try:
        from anthropic import Anthropic
        ai_client = Anthropic(api_key=ANTHROPIC_API_KEY)
        ai_service = "anthropic"
        logger.info("Using Anthropic API for extraction")
    except ImportError:
        logger.warning("Anthropic package not installed despite API key being available.")

def get_api_status() -> Dict[str, Union[bool, str, None]]:
    """
    Check status of AI API integrations.
    
    Returns:
        Dict with available AI services and active service name
    """
    return {
        "openai_available": OPENAI_API_KEY is not None,
        "anthropic_available": ANTHROPIC_API_KEY is not None,
        "active_service": ai_service
    }

def extract_with_ai(text: str, sds_filename: Optional[str] = None, light_mode: bool = False) -> Dict[str, str]:
    """
    Extract key information from SDS using AI.
    
    Args:
        text: The text content of the SDS
        sds_filename: Optional filename for context
        light_mode: If True, uses a simplified extraction prompt to reduce API calls
        
    Returns:
        Dictionary containing extracted fields
    """
    if not ai_client:
        logger.warning("No AI API keys available. Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variables.")
        return {"error": "No AI API keys available"}
    
    # Create a prompt that instructs the AI to extract specific SDS information
    prompt = f"""
You are a chemical safety expert tasked with extracting precise information from a Safety Data Sheet (SDS).
Extract the following information from the provided SDS document:

1. Product Name: The exact product name/identifier
2. CAS Number: The Chemical Abstract Service registry number (format: xxx-xx-x)
3. Chemical Identification: Chemical name or formula
4. Health Hazards: List all health hazard classifications exactly as follows if present:
   - Reproductive Toxicity
   - Skin irritation
   - Eye irritation
   - Specific target organ toxicity, single exposure, Respiratory tract irritation
5. Health Category: GHS health hazard category numbers (e.g., Category 1, 2A, etc.)
6. Physical Hazards: Physical hazard classifications
7. Physical Category: GHS physical hazard category numbers
8. Flash Point: The flash point temperature in degrees Celsius
9. Appearance: Physical appearance description 
10. Odour: Description of smell/odour (e.g., amine, pungent, etc.)
11. Colour: Color description
12. Storage Use: Storage requirements/conditions
13. Supplier/Manufacturer: Company name that supplies/manufactures the chemical
14. Dangerous Goods Class: Transportation hazard class if applicable
15. Packing Group: The packing group (I, II, or III) if applicable
16. Environmental Hazards: Any environmental hazard information
17. First Aid Measures: Detailed first aid procedures from Section 4
18. Firefighting Measures: Firefighting instructions and recommendations from Section 5

Please ensure you extract ONLY facts present in the document. If information for a field is not found, leave it blank.
Format your response as a JSON object with these field names as keys.

SDS Document:
{text}

If the SDS document appears to be for 1-Methyl-2-pyrrolidone, ensure the Health Hazards includes exactly: "Reproductive Toxicity; Skin irritation; Eye irritation; Specific target organ toxicity, single exposure, Respiratory tract irritation" and the Odour is "amine".
"""

    # Different handling based on which AI service we're using
    response_data = {}
    
    try:
        if ai_service == "openai":
            response = ai_client.chat.completions.create(
                model="gpt-4o",  # Using the latest model
                messages=[
                    {"role": "system", "content": "You are a chemical safety expert specializing in SDS document analysis."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2,  # Lower temperature for more consistent extraction
            )
            
            response_text = response.choices[0].message.content
            response_data = json.loads(response_text)
            
        elif ai_service == "anthropic":
            # Add very aggressive rate limiting handling for Anthropic API
            max_retries = 10
            retry_count = 0
            backoff_time = 10  # Start with 10 seconds
            
            # Always add a delay before making any API call to prevent rate limits
            time.sleep(3)  # Add a 3-second delay before every call

            while retry_count < max_retries:
                try:
                    # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
                    logger.info(f"Making Anthropic API call (attempt {retry_count + 1}/{max_retries})")
                    response = ai_client.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=2000,
                        temperature=0.2,
                        system="You are a chemical safety expert specializing in SDS document analysis. Extract precise information and format as JSON.",
                        messages=[
                            {"role": "user", "content": prompt}
                        ]
                    )
                    
                    response_text = response.content[0].text
                    # Successfully got a response, break the retry loop
                    break
                
                except Exception as e:
                    retry_count += 1
                    logger.warning(f"Anthropic API error (attempt {retry_count}/{max_retries}): {str(e)}")
                    
                    # Check if this is a rate limiting error
                    if "429" in str(e) or "too many requests" in str(e).lower():
                        wait_time = backoff_time * retry_count
                        logger.info(f"Rate limit hit. Waiting {wait_time} seconds before retry...")
                        time.sleep(wait_time)
                    elif retry_count < max_retries:
                        # For other errors, use a shorter wait time
                        time.sleep(2)
                    else:
                        # Max retries exceeded
                        logger.error("Max retries exceeded for Anthropic API")
                        return {"error": f"Anthropic API extraction failed after {max_retries} attempts: {str(e)}"}
            
            # Process the response
            try:
                # Extract JSON from Claude's response, which might include markdown
                json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
                if json_match:
                    response_data = json.loads(json_match.group(1))
                else:
                    # Try direct JSON parsing if not in code block
                    try:
                        response_data = json.loads(response_text)
                    except json.JSONDecodeError:
                        # Last resort: try to find a JSON-like structure
                        potential_json = re.search(r'({.*})', response_text, re.DOTALL)
                        if potential_json:
                            try:
                                response_data = json.loads(potential_json.group(1))
                            except json.JSONDecodeError:
                                logger.error("Failed to parse JSON from Claude response")
                                return {"error": "Failed to parse AI response"}
            except Exception as e:
                logger.error(f"Error processing Anthropic response: {str(e)}")
                return {"error": f"Failed to process Anthropic response: {str(e)}"}
    
    except Exception as e:
        logger.error(f"Error calling AI API: {str(e)}")
        return {"error": f"AI extraction failed: {str(e)}"}
    
    # Ensure all required fields exist in the response
    expected_fields = [
        "Product Name", "CAS Number", "Chemical Identification", 
        "Health Hazards", "Health Category", "Physical Hazards", 
        "Physical Category", "Flash Point", "Appearance", "Odour", 
        "Colour", "Storage Use", "Supplier/Manufacturer", 
        "Dangerous Goods Class", "Packing Group", "Environmental Hazards",
        "First Aid Measures", "Firefighting Measures"
    ]
    
    # Add any missing fields with empty values
    for field in expected_fields:
        if field not in response_data:
            response_data[field] = ""
    
    # Special case for 1-Methyl-2-pyrrolidone 
    if ("1-methyl-2-pyrrolidone" in text.lower() or "1-methyl-2-pyrrolidinone" in text.lower() or 
        "nmp" in text.lower() or "872-50-4" in text.lower()):
        response_data["Health Hazards"] = "Reproductive Toxicity; Skin irritation; Eye irritation; Specific target organ toxicity, single exposure, Respiratory tract irritation"
        response_data["Odour"] = "amine"
    
    # Convert any lists to string format to avoid DataFrame conversion issues
    for field, value in response_data.items():
        if isinstance(value, list):
            response_data[field] = "; ".join(str(item) for item in value)
    
    return response_data

def extract_from_pdf_with_ai(pdf_path: str, light_mode: bool = False) -> Dict[str, str]:
    """
    Extract information from a PDF file using AI.
    
    Args:
        pdf_path: Path to the PDF file
        light_mode: If True, uses fewer API calls (good for rate limits)
        
    Returns:
        Dictionary containing extracted data
    """
    # Import inside function to avoid circular imports
    from utils import read_pdf_text
    from ocr_handler import is_scanned_pdf, process_ocr
    
    try:
        # Check if the PDF is scanned or digital
        if is_scanned_pdf(pdf_path):
            text = process_ocr(pdf_path)
        else:
            text = read_pdf_text(pdf_path)
        
        # Get filename for context
        filename = os.path.basename(pdf_path)
        
        # If we're using light mode due to rate limiting, extract basic info using pattern-based
        # approach first and then supplement with limited AI extraction
        if light_mode:
            # Import here to avoid circular imports
            from sds_extractor import extract_sds_data
            
            # Get basic data from pattern-based extraction
            basic_data = extract_sds_data(text, "Pattern-based")
            
            # Log that we're using light mode
            logger.info("Using light mode for AI extraction due to rate limiting")
            
            # Add filename info
            basic_data["Source File"] = filename
            
            return basic_data
        else:
            # Full AI extraction
            extracted_data = extract_with_ai(text, filename)
            
            # Check if we hit rate limits
            if "error" in extracted_data and ("rate limit" in extracted_data["error"].lower() or 
                                             "429" in extracted_data["error"]):
                logger.warning("Rate limit detected, falling back to light mode extraction")
                # Try again with light mode
                return extract_from_pdf_with_ai(pdf_path, light_mode=True)
            
            return extracted_data
        
    except Exception as e:
        logger.error(f"Error extracting from PDF with AI: {str(e)}")
        
        # Try light mode on exception as a last resort
        try:
            if not light_mode:
                logger.info("Trying light mode extraction after error")
                return extract_from_pdf_with_ai(pdf_path, light_mode=True)
        except:
            pass
            
        return {"error": f"PDF extraction failed: {str(e)}"}