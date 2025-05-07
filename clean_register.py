"""
Script to clean and fix the SDS register CSV file by removing duplicate columns
and standardizing the format.
"""

import pandas as pd
import os
import sys

def clean_csv_register(input_file='data/sds_register.csv', output_file=None):
    """
    Clean the SDS register CSV file by removing duplicate columns
    and standardizing the format.
    
    Args:
        input_file: Path to the CSV file to clean
        output_file: Path to save the cleaned CSV file (defaults to overwriting input file)
        
    Returns:
        True if successful, False otherwise
    """
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        return False
    
    # If no output file is specified, overwrite the input file
    if output_file is None:
        output_file = input_file
    
    try:
        # Read the CSV file
        print(f"Reading CSV file: {input_file}")
        df = pd.read_csv(input_file)
        print(f"Original CSV has {len(df)} rows and {len(df.columns)} columns")
        
        # Standard columns we want in the output (in order)
        standard_columns = [
            'Number',
            'Product Name',
            'Supplier/Manufacturer',
            'CAS Number',
            'Chemical ID',
            'Location',
            'SDS Available',
            'Issue Date',
            'Health Hazards',
            'Health Category',
            'Physical Hazards',
            'Physical Category',
            'Hazardous Substance',
            'Flash Point (Deg C)',
            'Dangerous Goods Class',
            'Description',
            'Packing Group',
            'Appearance',
            'Colour',
            'Odour',
            'First Aid Measures',
            'Firefighting Measures',
            'Storage Use',
            'Environmental Hazards',
            'Source File',
            'Last Updated Date'
        ]
        
        # Create a new empty dataframe with the standard columns
        clean_df = pd.DataFrame(index=df.index, columns=standard_columns)
        
        # Display the original column names
        print("Original columns:")
        for col in df.columns:
            print(f"  - {col}")
        
        # Map from lowercase/snake_case to our standard column names
        column_mapping = {
            # Standard lowercase/snake_case fields
            'number': 'Number',
            'product_name': 'Product Name',
            'supplier_manufacturer': 'Supplier/Manufacturer',
            'cas_number': 'CAS Number',
            'chemical_identification': 'Chemical ID',
            'Chemical Identification': 'Chemical ID',
            'hazards': 'Hazards',
            'location': 'Location',
            'sds_available': 'SDS Available',
            'issue_date': 'Issue Date',
            'health_hazards': 'Health Hazards',
            'health_category': 'Health Category',
            'physical_hazards': 'Physical Hazards',
            'physical_category': 'Physical Category',
            'hazardous_substance': 'Hazardous Substance',
            'flash_point': 'Flash Point (Deg C)',
            'Flash Point': 'Flash Point (Deg C)',
            'dangerous_goods_class': 'Dangerous Goods Class',
            'description': 'Description',
            'packing_group': 'Packing Group',
            'appearance': 'Appearance',
            'colour': 'Colour',
            'odour': 'Odour',
            'first_aid_measures': 'First Aid Measures',
            'First Aid Measures': 'First Aid Measures',
            'firefighting_measures': 'Firefighting Measures',
            'Firefighting Measures': 'Firefighting Measures',
            'Storage Use': 'Storage Use',
            'Environmental Hazards': 'Environmental Hazards',
            'Source File': 'Source File',
            'Last Updated Date': 'Last Updated Date',
            
            # Title case versions
            'Number': 'Number',
            'Product Name': 'Product Name',
            'Supplier/Manufacturer': 'Supplier/Manufacturer',
            'CAS Number': 'CAS Number',
            'Health Hazards': 'Health Hazards',
            'Health Category': 'Health Category',
            'Physical Hazards': 'Physical Hazards',
            'Physical Category': 'Physical Category',
            'Appearance': 'Appearance',
            'Colour': 'Colour',
            'Odour': 'Odour',
        }
        
        # First fill in the new dataframe from the old one
        # For each target column, choose the best source column
        for target_col in standard_columns:
            # Find all possible source columns for this target
            sources = [source for source, target in column_mapping.items() 
                      if target == target_col and source in df.columns]
            
            if not sources:
                print(f"No matching source column found for '{target_col}'")
                continue
                
            # Prefer title case sources over snake_case sources
            title_case_sources = [s for s in sources if s[0].isupper()]
            snake_case_sources = [s for s in sources if not s[0].isupper()]
            
            # Choose the source based on preference
            if title_case_sources:
                # Prefer exact column name match if available
                if target_col in title_case_sources:
                    chosen_source = target_col
                else:
                    chosen_source = title_case_sources[0]
            elif snake_case_sources:
                chosen_source = snake_case_sources[0]
            else:
                chosen_source = sources[0]
            
            # Copy data from chosen source to target
            print(f"Using '{chosen_source}' as source for '{target_col}'")
            clean_df[target_col] = df[chosen_source]
        
        # Generate sequential numbers if missing
        if clean_df['Number'].isna().all() or (clean_df['Number'].astype(str) == '').all():
            clean_df['Number'] = range(1, len(clean_df) + 1)
            
        # Save the cleaned dataframe
        print(f"Saving cleaned CSV to {output_file}")
        clean_df.to_csv(output_file, index=False, quoting=1)  # Use quoting for all text fields
        
        print(f"Cleaned CSV has {len(clean_df)} rows and {len(clean_df.columns)} columns")
        return True
        
    except Exception as e:
        print(f"Error cleaning CSV: {str(e)}")
        return False

if __name__ == "__main__":
    # Allow specifying input and output files via command line arguments
    input_file = 'data/sds_register.csv'
    output_file = None
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    clean_csv_register(input_file, output_file)