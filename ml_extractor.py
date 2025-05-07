"""
Advanced machine learning extraction module for Safety Data Sheets.
This module provides enhanced extraction capabilities using state-of-the-art ML models.
"""

import os
import json
import re
import logging
from typing import Dict, List, Optional, Tuple, Union, Any

# Import base AI extractor functions
from ai_extractor import get_api_status, ai_service, ai_client, extract_with_ai

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Model configuration and selection
ML_MODELS = {
    "openai": {
        "standard": "gpt-4o",             # Default model
        "advanced": "gpt-4o",             # Advanced model for complex extraction
        "vision": "gpt-4o",               # Model with vision capabilities
        "specialized": "gpt-4o"           # Model for specialized extraction tasks
    },
    "anthropic": {
        "standard": "claude-3-5-sonnet-20241022",    # Default model
        "advanced": "claude-3-5-sonnet-20241022",    # Advanced model for complex extraction
        "vision": "claude-3-5-sonnet-20241022",      # Model with vision capabilities
        "specialized": "claude-3-5-sonnet-20241022"  # Model for specialized extraction tasks
    }
}

# Extraction strategies
EXTRACTION_STRATEGIES = [
    "direct_extraction",
    "hierarchical_extraction",
    "specialized_extraction",
    "multi_pass_extraction"
]

def get_available_ml_models() -> Dict[str, List[str]]:
    """
    Get available ML models for extraction.
    
    Returns:
        Dict of available models by service
    """
    if ai_service == "openai":
        return {"openai": list(ML_MODELS["openai"].keys())}
    elif ai_service == "anthropic":
        return {"anthropic": list(ML_MODELS["anthropic"].keys())}
    else:
        return {}

def get_ml_extraction_strategies() -> List[str]:
    """
    Get available extraction strategies.
    
    Returns:
        List of strategy names
    """
    return EXTRACTION_STRATEGIES

def specialized_hazard_extraction(text: str) -> Dict[str, Any]:
    """
    Specialized extraction of hazard information using domain-specific prompts.
    
    Args:
        text: SDS text content
        
    Returns:
        Dictionary with extracted hazard data
    """
    if not ai_client:
        return {"error": "No AI service available"}
    
    prompt = """
    Analyze this Safety Data Sheet text and extract ONLY the following hazard information:
    
    1. GHS Classification: List all GHS hazard classifications (e.g., Flammable liquid Category 2)
    2. Signal Word: The signal word (Danger or Warning)
    3. Hazard Statements: All H-statements with codes (e.g., H225: Highly flammable liquid and vapor)
    4. Precautionary Statements: All P-statements with codes 
    5. Pictograms: All applicable GHS pictograms (e.g., Flame, Health Hazard, Exclamation Mark)
    6. Health Hazards: Any health hazard classifications or statements (e.g., Acute toxicity Category 3, Skin corrosion Category 1A)
    7. Health Category: Highest category number for health hazards (e.g., "1" for most severe or "4" for least severe)
    8. Physical Hazards: Any physical hazard classifications (e.g., Flammable liquid Category 2, Explosive Division 1.1)
    9. Physical Category: Highest category number for physical hazards
    
    Format as JSON with these exact keys. If information is not found, use empty strings or arrays.
    
    Safety Data Sheet text:
    """
    
    hazard_data = {}
    
    try:
        if ai_service == "openai":
            response = ai_client.chat.completions.create(
                model=ML_MODELS["openai"]["specialized"],
                messages=[
                    {"role": "system", "content": "You are a chemical safety expert specializing in GHS hazard classification."},
                    {"role": "user", "content": prompt + text}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            hazard_data = json.loads(response.choices[0].message.content)
            
        elif ai_service == "anthropic":
            response = ai_client.messages.create(
                model=ML_MODELS["anthropic"]["specialized"],
                max_tokens=1500,
                temperature=0.1,
                system="You are a chemical safety expert specializing in GHS hazard classification. Respond only with JSON.",
                messages=[
                    {"role": "user", "content": prompt + text}
                ]
            )
            
            # Parse JSON from response
            response_text = response.content[0].text
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                hazard_data = json.loads(json_match.group(1))
            else:
                try:
                    hazard_data = json.loads(response_text)
                except:
                    # Try to find a JSON-like structure
                    potential_json = re.search(r'({.*})', response_text, re.DOTALL)
                    if potential_json:
                        try:
                            hazard_data = json.loads(potential_json.group(1))
                        except:
                            logger.error("Failed to parse JSON from hazard extraction")
                            
    except Exception as e:
        logger.error(f"Error in specialized hazard extraction: {str(e)}")
        hazard_data = {"error": str(e)}
    
    return hazard_data

def specialized_first_aid_extraction(text: str) -> Dict[str, Any]:
    """
    Specialized extraction of first aid information with structured output.
    
    Args:
        text: SDS text content
        
    Returns:
        Dictionary with structured first aid measures
    """
    if not ai_client:
        return {"error": "No AI service available"}
    
    prompt = """
    Extract detailed first aid measures from this Safety Data Sheet. 
    Focus on Section 4: First Aid Measures only.
    
    Create a structured JSON response with these categories:
    - Inhalation: First aid measures for inhalation exposure
    - Skin Contact: First aid measures for skin contact
    - Eye Contact: First aid measures for eye contact
    - Ingestion: First aid measures for ingestion
    - General Advice: Any general first aid advice provided
    - Notes to Physician: Any notes for medical professionals
    
    Include the exact text from the SDS, not your own recommendations.
    If a category is not mentioned, leave it as an empty string.
    
    Safety Data Sheet text:
    """
    
    first_aid_data = {}
    
    try:
        if ai_service == "openai":
            response = ai_client.chat.completions.create(
                model=ML_MODELS["openai"]["specialized"],
                messages=[
                    {"role": "system", "content": "You are a chemical safety expert specializing in first aid procedures."},
                    {"role": "user", "content": prompt + text}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            first_aid_data = json.loads(response.choices[0].message.content)
            
        elif ai_service == "anthropic":
            response = ai_client.messages.create(
                model=ML_MODELS["anthropic"]["specialized"],
                max_tokens=1500,
                temperature=0.1,
                system="You are a chemical safety expert specializing in first aid procedures. Respond only with JSON.",
                messages=[
                    {"role": "user", "content": prompt + text}
                ]
            )
            
            # Parse JSON from response
            response_text = response.content[0].text
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                first_aid_data = json.loads(json_match.group(1))
            else:
                try:
                    first_aid_data = json.loads(response_text)
                except:
                    # Try to find a JSON-like structure
                    potential_json = re.search(r'({.*})', response_text, re.DOTALL)
                    if potential_json:
                        try:
                            first_aid_data = json.loads(potential_json.group(1))
                        except:
                            logger.error("Failed to parse JSON from first aid extraction")
                            
    except Exception as e:
        logger.error(f"Error in specialized first aid extraction: {str(e)}")
        first_aid_data = {"error": str(e)}
    
    return first_aid_data

def specialized_firefighting_extraction(text: str) -> Dict[str, Any]:
    """
    Specialized extraction of firefighting information with structured output.
    
    Args:
        text: SDS text content
        
    Returns:
        Dictionary with structured firefighting measures
    """
    if not ai_client:
        return {"error": "No AI service available"}
    
    prompt = """
    Extract detailed firefighting measures from this Safety Data Sheet. 
    Focus on Section 5: Firefighting Measures only.
    
    Create a structured JSON response with these categories:
    - Suitable Extinguishing Media: Recommended firefighting agents
    - Unsuitable Extinguishing Media: Extinguishing media to avoid
    - Special Hazards: Special hazards arising from the substance
    - Protective Equipment: Protective equipment for firefighters
    - Specific Methods: Specific firefighting methods or instructions
    - Additional Information: Any other relevant information
    
    Include the exact text from the SDS, not your own recommendations.
    If a category is not mentioned, leave it as an empty string.
    
    Safety Data Sheet text:
    """
    
    firefighting_data = {}
    
    try:
        if ai_service == "openai":
            response = ai_client.chat.completions.create(
                model=ML_MODELS["openai"]["specialized"],
                messages=[
                    {"role": "system", "content": "You are a chemical safety expert specializing in firefighting procedures."},
                    {"role": "user", "content": prompt + text}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            firefighting_data = json.loads(response.choices[0].message.content)
            
        elif ai_service == "anthropic":
            response = ai_client.messages.create(
                model=ML_MODELS["anthropic"]["specialized"],
                max_tokens=1500,
                temperature=0.1,
                system="You are a chemical safety expert specializing in firefighting procedures. Respond only with JSON.",
                messages=[
                    {"role": "user", "content": prompt + text}
                ]
            )
            
            # Parse JSON from response
            response_text = response.content[0].text
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                firefighting_data = json.loads(json_match.group(1))
            else:
                try:
                    firefighting_data = json.loads(response_text)
                except:
                    # Try to find a JSON-like structure
                    potential_json = re.search(r'({.*})', response_text, re.DOTALL)
                    if potential_json:
                        try:
                            firefighting_data = json.loads(potential_json.group(1))
                        except:
                            logger.error("Failed to parse JSON from firefighting extraction")
                            
    except Exception as e:
        logger.error(f"Error in specialized firefighting extraction: {str(e)}")
        firefighting_data = {"error": str(e)}
    
    return firefighting_data

def hierarchical_extraction(text: str) -> Dict[str, Any]:
    """
    Hierarchical extraction that first identifies sections, then extracts from each.
    This approach improves accuracy by focusing on one section at a time.
    
    Args:
        text: SDS text content
        
    Returns:
        Dictionary with consolidated extracted data
    """
    if not ai_client:
        return {"error": "No AI service available"}
    
    # First identify section locations
    section_prompt = """
    Analyze this Safety Data Sheet and identify the start and end positions of each of the following sections:
    
    1. Identification (Section 1)
    2. Hazard Identification (Section 2)
    3. Composition/Information on Ingredients (Section 3)
    4. First Aid Measures (Section 4)
    5. Firefighting Measures (Section 5)
    6. Accidental Release Measures (Section 6)
    7. Handling and Storage (Section 7)
    8. Exposure Controls/Personal Protection (Section 8)
    9. Physical and Chemical Properties (Section 9)
    
    For each section, provide the approximate paragraph numbers where they start and end.
    Format your response as JSON with section names as keys and objects containing "start" and "end" values.
    """
    
    sections = {}
    results = {}
    
    try:
        # Extract section positions
        if ai_service == "openai":
            response = ai_client.chat.completions.create(
                model=ML_MODELS["openai"]["advanced"],
                messages=[
                    {"role": "system", "content": "You are a document structure analyzer specializing in Safety Data Sheets."},
                    {"role": "user", "content": section_prompt + "\n\n" + text[:5000]}  # Limit initial analysis to first part
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            sections = json.loads(response.choices[0].message.content)
            
        elif ai_service == "anthropic":
            response = ai_client.messages.create(
                model=ML_MODELS["anthropic"]["advanced"],
                max_tokens=1000,
                temperature=0.1,
                system="You are a document structure analyzer specializing in Safety Data Sheets. Respond only with JSON.",
                messages=[
                    {"role": "user", "content": section_prompt + "\n\n" + text[:5000]}  # Limit initial analysis to first part
                ]
            )
            
            # Parse JSON from response
            response_text = response.content[0].text
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                sections = json.loads(json_match.group(1))
            else:
                try:
                    sections = json.loads(response_text)
                except:
                    logger.error("Failed to parse JSON from section identification")
        
        # Now extract each field category separately
        results = extract_identification_info(text)
        
        # Add hazard information
        hazard_data = specialized_hazard_extraction(text)
        if hazard_data and "error" not in hazard_data:
            if "GHS Classification" in hazard_data:
                results["Health Hazards"] = hazard_data.get("GHS Classification", "")
            if "Hazard Statements" in hazard_data:
                if isinstance(hazard_data["Hazard Statements"], list):
                    results["Hazard Statements"] = "; ".join(hazard_data["Hazard Statements"])
                else:
                    results["Hazard Statements"] = hazard_data["Hazard Statements"]
            if "Pictograms" in hazard_data:
                if isinstance(hazard_data["Pictograms"], list):
                    results["Pictograms"] = "; ".join(hazard_data["Pictograms"])
                else:
                    results["Pictograms"] = hazard_data["Pictograms"]
        
        # Add first aid information
        first_aid_data = specialized_first_aid_extraction(text)
        if first_aid_data and "error" not in first_aid_data:
            # Convert dict to string representation for database compatibility
            if isinstance(first_aid_data, dict):
                first_aid_str = "; ".join([f"{k}: {v}" for k, v in first_aid_data.items() if v])
                results["First Aid Measures"] = first_aid_str
            else:
                results["First Aid Measures"] = str(first_aid_data)
        
        # Add firefighting information
        firefighting_data = specialized_firefighting_extraction(text)
        if firefighting_data and "error" not in firefighting_data:
            # Convert dict to string representation for database compatibility
            if isinstance(firefighting_data, dict):
                firefighting_str = "; ".join([f"{k}: {v}" for k, v in firefighting_data.items() if v])
                results["Firefighting Measures"] = firefighting_str
            else:
                results["Firefighting Measures"] = str(firefighting_data)
            
        # Add physical/chemical properties extraction
        phys_chem_data = extract_physical_chemical_properties(text)
        if phys_chem_data and "error" not in phys_chem_data:
            for key, value in phys_chem_data.items():
                if key not in results or not results[key]:  # Don't overwrite existing values
                    results[key] = value
                    
    except Exception as e:
        logger.error(f"Error in hierarchical extraction: {str(e)}")
        results["error"] = f"Hierarchical extraction failed: {str(e)}"
    
    return results

def extract_identification_info(text: str) -> Dict[str, str]:
    """
    Extract identification information from SDS.
    
    Args:
        text: SDS text content
        
    Returns:
        Dictionary with extracted identification data
    """
    if not ai_client:
        return {"error": "No AI service available"}
    
    prompt = """
    Extract only the following basic identification information from this Safety Data Sheet:
    
    1. Product Name: The exact product name/identifier
    2. CAS Number: Chemical Abstract Service registry number (format: xxx-xx-x)
    3. Chemical Identification: Chemical name or formula
    4. Supplier/Manufacturer: Company name that supplies/manufactures the chemical
    5. Recommended Use: Intended use of the chemical
    
    Format your response as JSON with these exact field names.
    If information is not found, use empty strings.
    
    SDS Document text:
    """
    
    identification_data = {}
    
    try:
        if ai_service == "openai":
            response = ai_client.chat.completions.create(
                model=ML_MODELS["openai"]["advanced"],
                messages=[
                    {"role": "system", "content": "You are a chemical identification specialist."},
                    {"role": "user", "content": prompt + text[:3000]}  # Focus on beginning of document
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            identification_data = json.loads(response.choices[0].message.content)
            
        elif ai_service == "anthropic":
            response = ai_client.messages.create(
                model=ML_MODELS["anthropic"]["advanced"],
                max_tokens=1000,
                temperature=0.1,
                system="You are a chemical identification specialist. Respond only with JSON.",
                messages=[
                    {"role": "user", "content": prompt + text[:3000]}  # Focus on beginning of document
                ]
            )
            
            # Parse JSON from response
            response_text = response.content[0].text
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                identification_data = json.loads(json_match.group(1))
            else:
                try:
                    identification_data = json.loads(response_text)
                except:
                    # Try to find a JSON-like structure
                    potential_json = re.search(r'({.*})', response_text, re.DOTALL)
                    if potential_json:
                        try:
                            identification_data = json.loads(potential_json.group(1))
                        except:
                            logger.error("Failed to parse JSON from identification extraction")
                            
    except Exception as e:
        logger.error(f"Error in identification extraction: {str(e)}")
        identification_data = {"error": str(e)}
    
    return identification_data

def extract_physical_chemical_properties(text: str) -> Dict[str, str]:
    """
    Extract physical and chemical properties from SDS.
    
    Args:
        text: SDS text content
        
    Returns:
        Dictionary with extracted physical and chemical properties
    """
    if not ai_client:
        return {"error": "No AI service available"}
    
    prompt = """
    Extract only the following physical and chemical properties from this Safety Data Sheet (focus on Section 9):
    
    1. Appearance: Physical appearance description
    2. Colour: Color description
    3. Odour: Description of smell/odour
    4. pH: pH value
    5. Melting Point: Melting point in °C
    6. Boiling Point: Boiling point in °C
    7. Flash Point: Flash point in °C
    8. Density: Density value with units
    9. Solubility: Solubility description
    10. Vapour Pressure: Vapour pressure with units
    
    Format your response as JSON with these exact field names.
    If information is not found, use empty strings.
    
    SDS Document text:
    """
    
    physical_data = {}
    
    try:
        if ai_service == "openai":
            response = ai_client.chat.completions.create(
                model=ML_MODELS["openai"]["advanced"],
                messages=[
                    {"role": "system", "content": "You are a chemical properties specialist."},
                    {"role": "user", "content": prompt + text}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            physical_data = json.loads(response.choices[0].message.content)
            
        elif ai_service == "anthropic":
            response = ai_client.messages.create(
                model=ML_MODELS["anthropic"]["advanced"],
                max_tokens=1000,
                temperature=0.1,
                system="You are a chemical properties specialist. Respond only with JSON.",
                messages=[
                    {"role": "user", "content": prompt + text}
                ]
            )
            
            # Parse JSON from response
            response_text = response.content[0].text
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                physical_data = json.loads(json_match.group(1))
            else:
                try:
                    physical_data = json.loads(response_text)
                except:
                    # Try to find a JSON-like structure
                    potential_json = re.search(r'({.*})', response_text, re.DOTALL)
                    if potential_json:
                        try:
                            physical_data = json.loads(potential_json.group(1))
                        except:
                            logger.error("Failed to parse JSON from physical properties extraction")
                            
    except Exception as e:
        logger.error(f"Error in physical properties extraction: {str(e)}")
        physical_data = {"error": str(e)}
    
    return physical_data

def multi_pass_extraction(text: str) -> Dict[str, Any]:
    """
    Multi-pass extraction that combines results from multiple extraction attempts.
    
    Args:
        text: SDS text content
        
    Returns:
        Dictionary with consolidated extracted data
    """
    # Get basic extraction
    from ai_extractor import extract_with_ai
    basic_results = extract_with_ai(text)
    
    # Get hierarchical extraction
    hierarchical_results = hierarchical_extraction(text)
    
    # Get specialized extractions
    first_aid_data = specialized_first_aid_extraction(text)
    firefighting_data = specialized_firefighting_extraction(text)
    hazard_data = specialized_hazard_extraction(text)
    physical_data = extract_physical_chemical_properties(text)
    
    # Combine results, preferring more specific extractions
    combined_results = basic_results.copy()
    
    # Only update fields that are missing or empty in the basic results
    for key, value in hierarchical_results.items():
        if key not in combined_results or not combined_results[key]:
            combined_results[key] = value
    
    # Add specialized extraction results
    if first_aid_data and "error" not in first_aid_data:
        if isinstance(first_aid_data, dict):
            first_aid_str = "; ".join([f"{k}: {v}" for k, v in first_aid_data.items() if v])
            combined_results["First Aid Measures"] = first_aid_str
        else:
            combined_results["First Aid Measures"] = str(first_aid_data)
    
    if firefighting_data and "error" not in firefighting_data:
        if isinstance(firefighting_data, dict):
            firefighting_str = "; ".join([f"{k}: {v}" for k, v in firefighting_data.items() if v])
            combined_results["Firefighting Measures"] = firefighting_str
        else:
            combined_results["Firefighting Measures"] = str(firefighting_data)
    
    if hazard_data and "error" not in hazard_data:
        # Add structured hazard data
        if "Health Hazards" not in combined_results or not combined_results["Health Hazards"]:
            # Look for health hazards specifically
            health_hazards = []
            if isinstance(hazard_data.get("GHS Classification", ""), list):
                for classification in hazard_data.get("GHS Classification", []):
                    if any(health_term in classification.lower() for health_term in ["toxic", "health", "irritat", "corrosive", "sensitiz", "mutagen", "carcino", "reproduct", "damage"]):
                        health_hazards.append(classification)
            
            if health_hazards:
                combined_results["Health Hazards"] = "; ".join(health_hazards)
            else:
                combined_results["Health Hazards"] = hazard_data.get("GHS Classification", "")
        
        # Add Health Category if missing
        if "Health Category" not in combined_results or not combined_results["Health Category"]:
            # Try to extract a health category
            if isinstance(hazard_data.get("GHS Classification", ""), list):
                for classification in hazard_data.get("GHS Classification", []):
                    if "category" in classification.lower() and any(health_term in classification.lower() for health_term in ["toxic", "health", "irritat", "corrosive", "sensitiz"]):
                        category_match = re.search(r"category\s*(\d+)", classification.lower())
                        if category_match:
                            combined_results["Health Category"] = category_match.group(1)
                            break
        
        # Add Physical Hazards if missing
        if "Physical Hazards" not in combined_results or not combined_results["Physical Hazards"]:
            # Look for physical hazards specifically
            physical_hazards = []
            if isinstance(hazard_data.get("GHS Classification", ""), list):
                for classification in hazard_data.get("GHS Classification", []):
                    if any(physical_term in classification.lower() for physical_term in ["flammable", "explosive", "oxidiz", "gas", "pressure", "react", "peroxide", "corrosive"]):
                        physical_hazards.append(classification)
            
            if physical_hazards:
                combined_results["Physical Hazards"] = "; ".join(physical_hazards)
        
        # Add Physical Category if missing
        if "Physical Category" not in combined_results or not combined_results["Physical Category"]:
            # Try to extract a physical category
            if isinstance(hazard_data.get("GHS Classification", ""), list):
                for classification in hazard_data.get("GHS Classification", []):
                    if "category" in classification.lower() and any(physical_term in classification.lower() for physical_term in ["flammable", "explosive", "oxidiz", "gas", "pressure"]):
                        category_match = re.search(r"category\s*(\d+)", classification.lower())
                        if category_match:
                            combined_results["Physical Category"] = category_match.group(1)
                            break
        
        if "Hazard Statements" not in combined_results or not combined_results["Hazard Statements"]:
            if isinstance(hazard_data.get("Hazard Statements", ""), list):
                combined_results["Hazard Statements"] = "; ".join(hazard_data["Hazard Statements"])
            else:
                combined_results["Hazard Statements"] = hazard_data.get("Hazard Statements", "")
    
    if physical_data and "error" not in physical_data:
        for key, value in physical_data.items():
            if key not in combined_results or not combined_results[key]:
                combined_results[key] = value
    
    return combined_results

def extract_sds_with_ml(text: str, strategy: str = "multi_pass_extraction", light_mode: bool = False) -> Dict[str, Any]:
    """
    Main function to extract SDS data using advanced ML techniques.
    
    Args:
        text: The text content of the SDS
        strategy: Extraction strategy to use
        light_mode: If True, uses a simplified extraction to reduce API calls
        
    Returns:
        Dictionary containing extracted fields
    """
    print(f"DEBUG: ML extraction - strategy={strategy}, light_mode={light_mode}")
    logger.info(f"ML extraction starting - strategy={strategy}, light_mode={light_mode}")
    
    if not text:
        logger.error("No text provided for ML extraction")
        return {"error": "No text provided"}
        
    if not ai_client:
        logger.warning("No AI API keys available. Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variables.")
        return {"error": "No AI API keys available"}
    
    # Import the AI extraction function once at the beginning to avoid import issues
    from ai_extractor import extract_with_ai
    
    # For all ML extraction strategies, always use light_mode when requested
    # This ensures we don't hit API limits and provides a consistent behavior
    print(f"DEBUG: ML extraction requested with strategy={strategy}, light_mode={light_mode}")
    logger.info(f"ML extraction requested with strategy={strategy}, light_mode={light_mode}")
    
    try:
        # If light_mode is enabled, use the basic extraction to save API calls
        if light_mode:
            logger.info(f"Using light mode extraction (strategy={strategy})")
            print(f"DEBUG: Using light_mode with extract_with_ai")
            results = extract_with_ai(text, light_mode=True)
            
        # Otherwise use the full extraction strategy
        else:
            # Select extraction strategy
            if strategy == "direct_extraction":
                # Use the basic extraction from ai_extractor.py
                print(f"DEBUG: Using direct_extraction strategy")
                results = extract_with_ai(text)
                
            elif strategy == "hierarchical_extraction":
                print(f"DEBUG: Using hierarchical_extraction strategy")
                results = hierarchical_extraction(text)
                
            elif strategy == "specialized_extraction":
                # First get basic info
                print(f"DEBUG: Using specialized_extraction strategy")
                results = extract_with_ai(text)
                
                # Get specialized extractions for key sections
                first_aid_data = specialized_first_aid_extraction(text)
                if first_aid_data and "error" not in first_aid_data:
                    if isinstance(first_aid_data, dict):
                        first_aid_str = "; ".join([f"{k}: {v}" for k, v in first_aid_data.items() if v])
                        results["First Aid Measures"] = first_aid_str
                    else:
                        results["First Aid Measures"] = str(first_aid_data)
                    
                firefighting_data = specialized_firefighting_extraction(text)
                if firefighting_data and "error" not in firefighting_data:
                    if isinstance(firefighting_data, dict):
                        firefighting_str = "; ".join([f"{k}: {v}" for k, v in firefighting_data.items() if v])
                        results["Firefighting Measures"] = firefighting_str
                    else:
                        results["Firefighting Measures"] = str(firefighting_data)
                        
            elif strategy == "multi_pass_extraction":
                print(f"DEBUG: Using multi_pass_extraction strategy")
                results = multi_pass_extraction(text)
                
            else:
                # Default to basic extraction
                print(f"DEBUG: Using default extraction as strategy '{strategy}' was not recognized")
                results = extract_with_ai(text)
    
    except Exception as e:
        logger.error(f"Error in ML extraction: {str(e)}")
        print(f"DEBUG: Error in ML extraction: {str(e)}")
        # Fallback to basic extraction on error
        results = extract_with_ai(text, light_mode=True)
    
    # Ensure all required fields exist
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
        if field not in results:
            results[field] = ""
    
    # Convert any complex data types to strings for database compatibility
    for field, value in results.items():
        if isinstance(value, list):
            results[field] = "; ".join(str(item) for item in value)
        elif isinstance(value, dict):
            # Convert dictionary to string format for database compatibility
            dict_str = "; ".join([f"{k}: {v}" for k, v in value.items() if v])
            results[field] = dict_str
    
    return results

def extract_from_pdf_with_ml(pdf_path: str, strategy: str = "multi_pass_extraction", light_mode: bool = False) -> Dict[str, Any]:
    """
    Extract information from a PDF file using advanced ML.
    
    Args:
        pdf_path: Path to the PDF file
        strategy: Extraction strategy to use
        light_mode: If True, uses a simplified extraction to reduce API calls
        
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
        
        # Extract using ML
        return extract_sds_with_ml(text, strategy, light_mode=light_mode)
        
    except Exception as e:
        logger.error(f"Error extracting from PDF with ML: {str(e)}")
        return {"error": f"PDF extraction failed: {str(e)}"}