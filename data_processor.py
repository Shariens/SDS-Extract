import io
import os
import base64
import pandas as pd
from typing import Optional, List

def process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Process the dataframe for display and export.
    
    Args:
        df: The input dataframe with SDS data
        
    Returns:
        A processed dataframe
    """
    # Make a copy to avoid modifying the original
    processed_df = df.copy()
    
    # Define the expected columns based on the SDS Register template
    template_columns = [
        'Number', 'Product Name', 'Supplier/Manufacturer', 'Quantity', 'Location', 
        'SDS Available', 'Issue Date', 'Health Hazards', 'Health Category',
        'Physical Hazards', 'Physical Category', 'Hazardous Substance', 'Flash Point (Deg C)',
        'Dangerous Goods Class', 'Description', 'Packing Group', 'Appearance', 'Colour', 'Odour',
        'First Aid Measures', 'Firefighting Measures'
    ]
    
    # Map column names from extraction to template column names
    column_mapping = {
        'Vendor': 'Supplier/Manufacturer',
        'Vendor Manufacturer': 'Supplier/Manufacturer',
        'Manufacturer': 'Supplier/Manufacturer',
        'CAS Number': 'Description',
        'Quanity': 'Quantity',
        'Chemical Identification': 'Hazardous Substance',
        'Precautionary Statements': 'Physical Hazards',
        'First Aid Measures': 'First Aid Measures',
        'Firefighting Measures': 'Firefighting Measures',
        'Supplier Information': 'Supplier/Manufacturer',
        'Environmental Hazards': 'Physical Hazards',
        'Regulatory Compliance Information': 'Hazardous Substance',
        'Hazard Classification': 'Health Category',
        'Physical Hazard': 'Physical Hazards',
        'Hazard Statement': 'Health Hazards',
        'Dangerous Goods Cl': 'Dangerous Goods Class',
        'Storage Use': 'Physical Category',
        'Response Statement': 'Health Hazards',
        'NFPA Symbol': 'Physical Category',
        'Physical Catergory': 'Physical Category',
        'Health Catergory': 'Health Category',
        'Desciption': 'Description'
    }
    
    # Rename columns according to the mapping
    for old_col, new_col in column_mapping.items():
        if old_col in processed_df.columns and new_col not in processed_df.columns:
            processed_df = processed_df.rename(columns={old_col: new_col})
    
    # Ensure all required columns exist
    for col in template_columns:
        if col not in processed_df.columns:
            processed_df[col] = ''
    
    # If Number column is missing or empty, create it
    if 'Number' not in processed_df.columns or processed_df['Number'].isna().all() or (processed_df['Number'] == '').all():
        processed_df['Number'] = range(1, len(processed_df) + 1)
    
    # Fill NA/None values with empty strings
    processed_df = processed_df.fillna('')
    
    # Convert all values to strings
    for col in processed_df.columns:
        processed_df[col] = processed_df[col].astype(str)
    
    # Clean up whitespace
    for col in processed_df.columns:
        processed_df[col] = processed_df[col].str.strip()
    
    # Set default SDS Available to 'Yes' if empty
    if 'SDS Available' in processed_df.columns:
        processed_df.loc[processed_df['SDS Available'] == '', 'SDS Available'] = 'Yes'
    
    # Set default Issue Date to current date if empty
    if 'Issue Date' in processed_df.columns:
        import datetime
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        processed_df.loc[processed_df['Issue Date'] == '', 'Issue Date'] = today
    
    # Reorder columns to exactly match template order
    final_columns = []
    for col in template_columns:
        if col in processed_df.columns:
            final_columns.append(col)
    
    # Add any extra columns that weren't in the template
    extra_columns = [col for col in processed_df.columns if col not in template_columns]
    final_columns.extend(extra_columns)
    
    # Return with reordered columns
    return processed_df[final_columns]

def filter_dataframe(df: pd.DataFrame, column: str, value: Optional[str] = None) -> pd.DataFrame:
    """
    Filter the dataframe based on column and value.
    
    Args:
        df: The input dataframe
        column: Column to filter on
        value: Value to filter for (None to return all)
        
    Returns:
        A filtered dataframe
    """
    if value is None or value == "All" or column not in df.columns:
        return df
    
    return df[df[column] == value]

def clean_special_characters(text: str) -> str:
    """
    Clean and normalize special characters for Excel and CSV export.
    Specifically handles UTF-8 encoding issues, special characters, and chemical symbols.
    
    Args:
        text: The input text to clean
        
    Returns:
        Cleaned text with normalized special characters
    """
    if not isinstance(text, str):
        return str(text)
    
    # First handle common UTF-8 encoding issues
    # Fix common UTF-8 encoding problems like "â€""
    cleaned = text
    
    # Fix em-dash encoding issues (â€")
    cleaned = cleaned.replace('â€"', '-')
    cleaned = cleaned.replace('â€"', '-')  # Another variant
    cleaned = cleaned.replace('â€"', '-')
    
    # Fix other encoding issues
    cleaned = cleaned.replace('â€™', "'")
    cleaned = cleaned.replace('â€œ', '"')
    cleaned = cleaned.replace('â€', '"')
    cleaned = cleaned.replace('â€¦', '...')
    cleaned = cleaned.replace('â€¢', '*')  # Bullet point
    cleaned = cleaned.replace('â€¡', '‡')
    
    # Handle UTF-8 special character replacements
    cleaned = cleaned.replace('\u2013', '-')          # en dash
    cleaned = cleaned.replace('\u2014', '-')          # em dash (using single hyphen for consistency)
    cleaned = cleaned.replace('\u2018', "'")          # curly quotes
    cleaned = cleaned.replace('\u2019', "'")
    cleaned = cleaned.replace('\u201c', '"')
    cleaned = cleaned.replace('\u201d', '"')
    cleaned = cleaned.replace('\u00a0', ' ')          # non-breaking space
    cleaned = cleaned.replace('\u2022', '*')          # bullet point
    cleaned = cleaned.replace('\u2026', '...')        # ellipsis
    
    # Fix degree symbol and related issues
    cleaned = cleaned.replace('\u00c2', '')           # Remove Â character
    cleaned = cleaned.replace('\u00b0', '')           # Remove ° character
    cleaned = cleaned.replace('°C', ' C')             # Replace degree C with space C
    cleaned = cleaned.replace('°F', ' F')             # Replace degree F with space F
    cleaned = cleaned.replace('Â°C', ' C')            # Replace encoded degree C
    cleaned = cleaned.replace('Â°F', ' F')            # Replace encoded degree F
    
    # Handle special quotes and apostrophes
    cleaned = cleaned.replace('â€™', "'")
    cleaned = cleaned.replace('â€˜', "'")
    cleaned = cleaned.replace('â€œ', '"')
    cleaned = cleaned.replace('â€', '"')
    
    # Handle chemical subscripts and superscripts
    cleaned = cleaned.replace('₂', '2')
    cleaned = cleaned.replace('₃', '3')
    cleaned = cleaned.replace('₄', '4')
    cleaned = cleaned.replace('₅', '5')
    cleaned = cleaned.replace('₆', '6')
    cleaned = cleaned.replace('₈', '8')
    cleaned = cleaned.replace('₁', '1')
    cleaned = cleaned.replace('₇', '7')
    cleaned = cleaned.replace('₉', '9')
    cleaned = cleaned.replace('₀', '0')
    
    cleaned = cleaned.replace('¹', '1')
    cleaned = cleaned.replace('²', '2')
    cleaned = cleaned.replace('³', '3')
    cleaned = cleaned.replace('⁴', '4')
    cleaned = cleaned.replace('⁵', '5')
    cleaned = cleaned.replace('⁶', '6')
    cleaned = cleaned.replace('⁷', '7')
    cleaned = cleaned.replace('⁸', '8')
    cleaned = cleaned.replace('⁹', '9')
    cleaned = cleaned.replace('⁰', '0')
    cleaned = cleaned.replace('⁻', '-')
    
    # Handle common chemical formulas
    cleaned = cleaned.replace('(NH₄)₂S₂O₈', '(NH4)2S2O8')
    
    # Fix specific temperature values that might appear in Flash Point field
    cleaned = cleaned.replace('91Â°C', '91 C')
    
    # Fix other common special characters
    cleaned = cleaned.replace('±', '+/-')
    cleaned = cleaned.replace('×', 'x')
    cleaned = cleaned.replace('÷', '/')
    cleaned = cleaned.replace('µ', 'u')    # micro symbol to u
    cleaned = cleaned.replace('®', '(R)')  # Registered trademark
    cleaned = cleaned.replace('™', '(TM)') # Trademark
    cleaned = cleaned.replace('©', '(c)')  # Copyright
    
    # Fix Latin characters
    cleaned = cleaned.replace('á', 'a')
    cleaned = cleaned.replace('é', 'e')
    cleaned = cleaned.replace('í', 'i')
    cleaned = cleaned.replace('ó', 'o')
    cleaned = cleaned.replace('ú', 'u')
    cleaned = cleaned.replace('ñ', 'n')
    
    return cleaned

def convert_complex_types_to_string(value):
    """
    Convert complex data types like dictionaries and lists to readable strings.
    
    Args:
        value: The value to convert, can be any type
        
    Returns:
        A string representation of the value
    """
    if isinstance(value, dict):
        return '; '.join([f"{k}: {v}" for k, v in value.items() if v])
    elif isinstance(value, list):
        return '; '.join([str(item) for item in value if item])
    else:
        return str(value) if value is not None else ''


def clean_nan_values(df):
    """
    Clean NaN values from a dataframe, replacing them with empty strings.
    Also cleans string representations of NaN and None.
    
    Args:
        df: The dataframe to clean
        
    Returns:
        The cleaned dataframe
    """
    # First replace all NaN values with empty strings
    df = df.fillna('')
    
    # Then clean any string representations of 'nan' or 'None'
    for col in df.columns:
        # Replace with empty string if value is a string 'nan' or 'None'
        df[col] = df[col].apply(lambda x: '' if str(x).lower() == 'nan' or str(x).lower() == 'none' else x)
    
    return df

def generate_excel(df: pd.DataFrame) -> io.BytesIO:
    """
    Generate a completely fresh Excel file from extracted data.
    Uses only the available fields from the extraction process and places them
    in column A onward.
    
    Args:
        df: The dataframe with extracted SDS data
        
    Returns:
        BytesIO object containing the Excel file
    """
    # Debug information
    print("EXCEL EXPORT DEBUG INFO:")
    print(f"Input DataFrame shape: {df.shape}")
    print(f"Input DataFrame columns: {list(df.columns)}")
    
    # Create a completely new DataFrame with consistent column names
    # We'll merge both lowercase and titlecase versions of the same data
    export_df = pd.DataFrame()
    
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
    
    # APPROACH COMPLETELY CHANGED: Start with an empty dataframe
    # and only copy fields we want, taking the best version of each field
    export_df = pd.DataFrame(index=df.index, columns=standard_columns)
    
    # Make a copy and clean NaN values using our dedicated function
    df_clean = clean_nan_values(df.copy())
    
    # First convert any dictionaries or complex data types to strings
    for col in df_clean.columns:
        df_clean[col] = df_clean[col].apply(convert_complex_types_to_string)
    
    # Map from lowercase/snake_case to our standard column names
    column_mapping = {
        'number': 'Number',
        'product_name': 'Product Name',
        'Product Name': 'Product Name',
        'supplier_manufacturer': 'Supplier/Manufacturer',
        'Supplier/Manufacturer': 'Supplier/Manufacturer',
        'cas_number': 'CAS Number',
        'CAS Number': 'CAS Number',
        'Chemical Identification': 'Chemical ID',
        'hazardous_substance': 'Hazardous Substance',
        'hazards': 'Hazards',
        'health_hazards': 'Health Hazards',
        'Health Hazards': 'Health Hazards',
        'health_category': 'Health Category',
        'Health Category': 'Health Category',
        'physical_hazards': 'Physical Hazards',
        'Physical Hazards': 'Physical Hazards',
        'physical_category': 'Physical Category',
        'Physical Category': 'Physical Category',
        'flash_point': 'Flash Point (Deg C)',
        'Flash Point': 'Flash Point (Deg C)',
        'dangerous_goods_class': 'Dangerous Goods Class',
        'description': 'Description',
        'packing_group': 'Packing Group',
        'appearance': 'Appearance',
        'Appearance': 'Appearance',
        'colour': 'Colour',
        'Colour': 'Colour',
        'odour': 'Odour',
        'Odour': 'Odour',
        'location': 'Location',
        'sds_available': 'SDS Available',
        'issue_date': 'Issue Date',
        'first_aid_measures': 'First Aid Measures',
        'First Aid Measures': 'First Aid Measures',
        'firefighting_measures': 'Firefighting Measures',
        'Firefighting Measures': 'Firefighting Measures',
        'Storage Use': 'Storage Use',
        'Environmental Hazards': 'Environmental Hazards',
        'Source File': 'Source File', 
        'Last Updated Date': 'Last Updated Date'
    }
    
    # Now go through our mapping and copy data to the export dataframe
    # For each target column, look for the best source column to use
    for target_col in standard_columns:
        # Find all possible source columns that map to this target
        sources = [source for source, target in column_mapping.items() if target == target_col and source in df_clean.columns]
        
        if not sources:
            # No matching columns found, leave empty
            continue
            
        # Prefer title case over snake_case if both exist
        title_case_sources = [s for s in sources if s[0].isupper()]
        snake_case_sources = [s for s in sources if not s[0].isupper()]
        
        # Choose the source based on preference
        if title_case_sources:
            # Prefer the exact match of the column name if available
            if target_col in title_case_sources:
                chosen_source = target_col
            else:
                chosen_source = title_case_sources[0]
        elif snake_case_sources:
            chosen_source = snake_case_sources[0]
        else:
            # Use any available source
            chosen_source = sources[0]
        
        # Copy the data from chosen source
        print(f"Excel: Using '{chosen_source}' as source for '{target_col}'")
        export_df[target_col] = df_clean[chosen_source]
    
    # Assign sequential numbers if missing
    if export_df['Number'].isna().all() or (export_df['Number'] == '').all():
        export_df['Number'] = range(1, len(export_df) + 1)
    
    # Create a BytesIO object to store the Excel file
    output = io.BytesIO()
    
    try:
        # Clean data to prevent encoding issues
        for col in export_df.columns:
            # Use our dedicated special character cleaning function
            export_df[col] = export_df[col].apply(clean_special_characters)
        
        # Final cleanup - make absolutely sure there are no NaN values
        export_df = clean_nan_values(export_df)
        
        # Create an Excel writer with option to handle NaN/Inf values
        with pd.ExcelWriter(output, engine='xlsxwriter', engine_kwargs={'options': {'nan_inf_to_errors': True}}) as writer:
            # Write the dataframe to Excel without the index
            export_df.to_excel(writer, sheet_name='SDS Register', index=False)
            
            # Get the xlsxwriter workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets['SDS Register']
            
            # Add a header format
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#D7E4BC',
                'border': 1
            })
            
            # Add a normal data format with text wrapping
            data_format = workbook.add_format({
                'valign': 'top',
                'text_wrap': True,
                'border': 1
            })
            
            # Apply the header format to the header row
            for col_num, value in enumerate(export_df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            # Set column widths - more specific to match template
            column_widths = {
                'Number': 8,
                'Product Name': 30,
                'Supplier/Manufacturer': 20,
                'Quantity': 10,
                'Location': 12,
                'SDS Available': 12,
                'Issue Date': 12,
                'Health Hazards': 25,
                'Health Category': 15,
                'Physical Hazards': 25,
                'Physical Category': 15,
                'Hazardous Substance': 20,
                'Flash Point (Deg C)': 12,
                'Dangerous Goods Class': 15,
                'Description': 25,
                'Packing Group': 12,
                'Appearance': 15,
                'Colour': 15,
                'Odour': 15,
                'First Aid Measures': 25,
                'Firefighting Measures': 25
            }
            
            # Apply column widths
            for i, col in enumerate(export_df.columns):
                if col in column_widths:
                    worksheet.set_column(i, i, column_widths[col])
                else:
                    worksheet.set_column(i, i, 15)  # Default width
            
            # Add data with formatting
            for row_num in range(1, len(export_df) + 1):
                for col_num, col_name in enumerate(export_df.columns):
                    cell_value = export_df.iloc[row_num-1, col_num]
                    worksheet.write(row_num, col_num, cell_value, data_format)
        
        # Seek to the beginning of the stream
        output.seek(0)
        
    except Exception as e:
        print(f"Error generating Excel file: {e}")
        # Return an empty BytesIO if there was an error
        output = io.BytesIO()
        output.write(b"Error generating Excel file")
        output.seek(0)
    
    return output

def generate_csv(df: pd.DataFrame) -> io.StringIO:
    """
    Generate a CSV file from the dataframe with consistent column structure.
    Creates a brand new file with data starting from the first column.
    
    Args:
        df: The dataframe to export
        
    Returns:
        StringIO object containing the CSV file
    """
    # Debug information
    print("CSV EXPORT DEBUG INFO:")
    print(f"Input DataFrame shape: {df.shape}")
    print(f"Input DataFrame columns: {list(df.columns)}")
    
    # Create a completely new DataFrame with consistent column names
    # We'll merge both lowercase and titlecase versions of the same data
    export_df = pd.DataFrame()
    
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
    
    # APPROACH COMPLETELY CHANGED: Start with an empty dataframe
    # and only copy fields we want, taking the best version of each field
    export_df = pd.DataFrame(index=df.index, columns=standard_columns)
    
    # Make a copy and clean NaN values using our dedicated function
    df_clean = clean_nan_values(df.copy())
    
    # First convert any dictionaries or complex data types to strings
    for col in df_clean.columns:
        df_clean[col] = df_clean[col].apply(convert_complex_types_to_string)
    
    # Map from lowercase/snake_case to our standard column names
    column_mapping = {
        'number': 'Number',
        'product_name': 'Product Name',
        'Product Name': 'Product Name',
        'supplier_manufacturer': 'Supplier/Manufacturer',
        'Supplier/Manufacturer': 'Supplier/Manufacturer',
        'cas_number': 'CAS Number',
        'CAS Number': 'CAS Number',
        'Chemical Identification': 'Chemical ID',
        'hazardous_substance': 'Hazardous Substance',
        'hazards': 'Hazards',
        'health_hazards': 'Health Hazards',
        'Health Hazards': 'Health Hazards',
        'health_category': 'Health Category',
        'Health Category': 'Health Category',
        'physical_hazards': 'Physical Hazards',
        'Physical Hazards': 'Physical Hazards',
        'physical_category': 'Physical Category',
        'Physical Category': 'Physical Category',
        'flash_point': 'Flash Point (Deg C)',
        'Flash Point': 'Flash Point (Deg C)',
        'dangerous_goods_class': 'Dangerous Goods Class',
        'description': 'Description',
        'packing_group': 'Packing Group',
        'appearance': 'Appearance',
        'Appearance': 'Appearance',
        'colour': 'Colour',
        'Colour': 'Colour',
        'odour': 'Odour',
        'Odour': 'Odour',
        'location': 'Location',
        'sds_available': 'SDS Available',
        'issue_date': 'Issue Date',
        'first_aid_measures': 'First Aid Measures',
        'First Aid Measures': 'First Aid Measures',
        'firefighting_measures': 'Firefighting Measures',
        'Firefighting Measures': 'Firefighting Measures',
        'Storage Use': 'Storage Use',
        'Environmental Hazards': 'Environmental Hazards',
        'Source File': 'Source File', 
        'Last Updated Date': 'Last Updated Date'
    }
    
    # Now go through our mapping and copy data to the export dataframe
    # For each target column, look for the best source column to use
    for target_col in standard_columns:
        # Find all possible source columns that map to this target
        sources = [source for source, target in column_mapping.items() if target == target_col and source in df_clean.columns]
        
        if not sources:
            # No matching columns found, leave empty
            continue
            
        # Prefer title case over snake_case if both exist
        title_case_sources = [s for s in sources if s[0].isupper()]
        snake_case_sources = [s for s in sources if not s[0].isupper()]
        
        # Choose the source based on preference
        if title_case_sources:
            # Prefer the exact match of the column name if available
            if target_col in title_case_sources:
                chosen_source = target_col
            else:
                chosen_source = title_case_sources[0]
        elif snake_case_sources:
            chosen_source = snake_case_sources[0]
        else:
            # Use any available source
            chosen_source = sources[0]
        
        # Copy the data from chosen source
        print(f"CSV: Using '{chosen_source}' as source for '{target_col}'")
        export_df[target_col] = df_clean[chosen_source]
    
    # Assign sequential numbers if missing
    if export_df['Number'].isna().all() or (export_df['Number'] == '').all():
        export_df['Number'] = range(1, len(export_df) + 1)
    
    # Create a StringIO object to store the CSV content
    output = io.StringIO()
    
    try:
        # Clean data to prevent encoding issues
        for col in export_df.columns:
            # Use our dedicated special character cleaning function
            export_df[col] = export_df[col].apply(clean_special_characters)
        
        # Final cleanup - make absolutely sure there are no NaN values
        export_df = clean_nan_values(export_df)
        
        # Convert dataframe to CSV with all text fields quoted
        export_df.to_csv(output, index=False, quoting=1)  # quoting=1 means quote all non-numeric fields
        
        # Seek to the beginning of the stream
        output.seek(0)
        
    except Exception as e:
        print(f"Error generating CSV file: {e}")
        # Return an empty StringIO if there was an error
        output = io.StringIO()
        output.write("Error generating CSV file")
        output.seek(0)
    
    return output