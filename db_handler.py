"""
SQLite database handler for the SDS Data Extractor application.
This module provides functionality to store and retrieve SDS data from a SQLite database.
"""

import os
import json
import sqlite3
import logging
import pandas as pd
from typing import Tuple, List, Dict, Optional, Any, Union

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database configuration
DB_DIR = "data"
DB_FILE = os.path.join(DB_DIR, "sds_database.sqlite")
DB_VERSION = 1

def ensure_db_exists() -> None:
    """
    Ensure the database directory and file exist, creating them if necessary.
    """
    # Create data directory if it doesn't exist
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)

def get_connection() -> sqlite3.Connection:
    """
    Get a connection to the SQLite database.
    
    Returns:
        sqlite3.Connection: An active database connection
    """
    ensure_db_exists()
    conn = sqlite3.connect(DB_FILE)
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def initialize_database() -> Tuple[bool, str]:
    """
    Initialize the database schema if it doesn't already exist.
    
    Returns:
        Tuple[bool, str]: A tuple of (success, message)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Create settings table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create SDS register table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sds_register (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number TEXT,
            product_name TEXT,
            supplier_manufacturer TEXT,
            hazards TEXT,
            location TEXT,
            sds_available TEXT,
            issue_date TEXT,
            health_hazards TEXT,
            health_category TEXT,
            physical_hazards TEXT,
            physical_category TEXT,
            hazardous_substance TEXT,
            flash_point TEXT,
            dangerous_goods_class TEXT,
            description TEXT,
            packing_group TEXT,
            appearance TEXT,
            colour TEXT,
            odour TEXT,
            cas_number TEXT,
            first_aid_measures TEXT,
            firefighting_measures TEXT,
            additional_info TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create extraction history table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS extraction_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            timestamp TEXT,
            extraction_method TEXT,
            success INTEGER,
            fields_extracted TEXT,
            additional_info TEXT
        )
        ''')
        
        # Set the database version if it doesn't exist
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", 
                      ("db_version", str(DB_VERSION)))
        
        conn.commit()
        conn.close()
        
        return True, "Database initialized successfully"
    except Exception as e:
        error_message = f"Error initializing database: {e}"
        print(error_message)
        return False, error_message

def save_to_database(df: pd.DataFrame, history: List[Dict] = None) -> Tuple[bool, str]:
    """
    Save a dataframe to the SQLite database.
    
    Args:
        df: The pandas DataFrame containing SDS data
        history: Optional extraction history to save
        
    Returns:
        Tuple[bool, str]: A tuple of (success, message)
    """
    try:
        conn = get_connection()
        
        # First, delete all existing records
        # For a production app, you might want a more sophisticated approach
        conn.execute("DELETE FROM sds_register")
        
        # Convert DataFrame to list of dictionaries for insertion
        records = df.to_dict(orient='records')
        
        # Map DataFrame columns to database columns, keeping them in their original format
        # Note: We've changed our approach to keep column names consistent throughout the app
        # This prevents duplication issues during export
        column_mapping = {
            # Standard snake_case columns defined in the schema
            'number': 'number',
            'product_name': 'product_name',
            'supplier_manufacturer': 'supplier_manufacturer',
            'hazards': 'hazards',
            'location': 'location',
            'sds_available': 'sds_available',
            'issue_date': 'issue_date',
            'health_hazards': 'health_hazards',
            'health_category': 'health_category',
            'physical_hazards': 'physical_hazards',
            'physical_category': 'physical_category',
            'hazardous_substance': 'hazardous_substance',
            'flash_point': 'flash_point',
            'dangerous_goods_class': 'dangerous_goods_class',
            'description': 'description',
            'packing_group': 'packing_group',
            'appearance': 'appearance',
            'colour': 'colour',
            'odour': 'odour',
            'cas_number': 'cas_number',
            'first_aid_measures': 'first_aid_measures',
            'firefighting_measures': 'firefighting_measures',
            
            # Alternative title-case keys - map to the same column names
            'Number': 'number',
            'Product Name': 'product_name',
            'Supplier/Manufacturer': 'supplier_manufacturer',
            'Hazards': 'hazards',
            'Location': 'location',
            'SDS Available': 'sds_available',
            'Issue Date': 'issue_date',
            'Health Hazards': 'health_hazards',
            'Health Category': 'health_category',
            'Physical Hazards': 'physical_hazards',
            'Physical Category': 'physical_category',
            'Hazardous Substance': 'hazardous_substance',
            'Flash Point (Deg C)': 'flash_point',
            'Dangerous Goods Class': 'dangerous_goods_class',
            'Description': 'description',
            'Packing Group': 'packing_group',
            'Appearance': 'appearance',
            'Colour': 'colour',
            'Odour': 'odour',
            'CAS Number': 'cas_number',
            'First Aid Measures': 'first_aid_measures',
            'Firefighting Measures': 'firefighting_measures'
        }
        
        # For each record, prepare and insert data
        for record in records:
            # Prepare record with correct column names
            db_record = {}
            for df_col, db_col in column_mapping.items():
                if df_col in record:
                    # Serialize complex data types
                    value = record[df_col]
                    if isinstance(value, dict):
                        value = json.dumps(value)
                    elif isinstance(value, list):
                        value = "; ".join([str(item) for item in value])
                    db_record[db_col] = value
                    
            # Additional columns not in the mapping
            for col in record:
                if col not in column_mapping.keys():
                    # Store any non-mapped columns in additional_info as JSON
                    if 'additional_info' not in db_record:
                        db_record['additional_info'] = json.dumps({})
                    
                    # Load existing additional_info, update it, and save back
                    additional_info = json.loads(db_record['additional_info'])
                    additional_info[col] = record[col]
                    db_record['additional_info'] = json.dumps(additional_info)
            
            # Create placeholders for SQL query
            placeholders = ', '.join(['?'] * len(db_record))
            columns = ', '.join(db_record.keys())
            
            # Execute insert
            query = f"INSERT INTO sds_register ({columns}) VALUES ({placeholders})"
            conn.execute(query, list(db_record.values()))
        
        # Save extraction history if provided
        if history:
            for entry in history:
                # Convert the fields_extracted dict to JSON string
                if 'fields_extracted' in entry and isinstance(entry['fields_extracted'], dict):
                    entry['fields_extracted'] = json.dumps(entry['fields_extracted'])
                
                # Convert any additional info to JSON if needed
                if 'additional_info' in entry and isinstance(entry['additional_info'], dict):
                    entry['additional_info'] = json.dumps(entry['additional_info'])
                
                # Insert the history entry
                conn.execute('''
                INSERT INTO extraction_history 
                (filename, timestamp, extraction_method, success, fields_extracted, additional_info)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    entry.get('filename', ''),
                    entry.get('timestamp', ''),
                    entry.get('extraction_method', ''),
                    1 if entry.get('success', False) else 0,
                    entry.get('fields_extracted', '{}'),
                    entry.get('additional_info', '{}')
                ))
        
        conn.commit()
        conn.close()
        
        return True, f"Data saved to SQLite database: {os.path.abspath(DB_FILE)}"
    except Exception as e:
        error_message = f"Error saving to database: {e}"
        print(error_message)
        return False, error_message

def load_from_database() -> Tuple[Optional[pd.DataFrame], List[Dict]]:
    """
    Load SDS data from the SQLite database.
    
    Returns:
        Tuple[Optional[pd.DataFrame], List[Dict]]: A tuple of (dataframe, history)
    """
    try:
        # Initialize the database if it doesn't exist
        initialize_database()
        
        conn = get_connection()
        
        # Load the SDS register data
        df = pd.read_sql_query("SELECT * FROM sds_register", conn)
        
        # Remove SQLite-specific columns
        if 'id' in df.columns:
            df = df.drop('id', axis=1)
        if 'created_at' in df.columns:
            df = df.drop('created_at', axis=1)
        if 'updated_at' in df.columns:
            df = df.drop('updated_at', axis=1)
            
        # Create a brand new dataframe with only the standard columns
        # This ensures consistent column ordering and prevents the column U issue
        new_df = pd.DataFrame()
        
        # Extract both standard columns and additional_info fields
        standard_columns = [
            'number', 'product_name', 'supplier_manufacturer', 'hazards', 
            'location', 'sds_available', 'issue_date', 'health_hazards', 
            'health_category', 'physical_hazards', 'physical_category', 
            'hazardous_substance', 'flash_point', 'dangerous_goods_class', 
            'description', 'packing_group', 'appearance', 'colour', 'odour',
            'cas_number', 'first_aid_measures', 'firefighting_measures'
        ]
        
        # First add standard columns that exist in the original dataframe
        for col in standard_columns:
            if col in df.columns:
                # Convert any complex data types to strings
                new_df[col] = df[col].apply(lambda x: 
                                         str(x) if isinstance(x, dict) else 
                                         '; '.join([str(i) for i in x]) if isinstance(x, list) else x)
        
        # Then extract and add additional_info data
        if 'additional_info' in df.columns:
            # For each row, extract additional_info JSON into separate columns
            for idx, row in df.iterrows():
                if pd.notna(row['additional_info']) and row['additional_info']:
                    try:
                        additional_info = json.loads(row['additional_info'])
                        for key, value in additional_info.items():
                            if idx >= len(new_df):
                                # Add a new row if needed
                                new_row = pd.Series([None] * len(new_df.columns), index=new_df.columns)
                                new_df = pd.concat([new_df, pd.DataFrame([new_row])], ignore_index=True)
                            
                            # Add the column if it doesn't exist
                            if key not in new_df.columns:
                                new_df[key] = None
                            
                            # Add the value
                            new_df.at[idx, key] = value
                    except (json.JSONDecodeError, TypeError):
                        # Handle invalid JSON
                        pass
        
        # If we don't have any standard columns, but do have rows from additional_info,
        # use the df from the database (this is a fallback)
        if len(new_df) == 0 and len(df) > 0:
            if 'additional_info' in df.columns:
                df = df.drop('additional_info', axis=1)
            new_df = df
        
        # IMPORTANT: We're no longer renaming columns when loading from the database
        # This prevents column duplication issues during export
        
        # Use the new dataframe without renaming columns
        df = new_df.copy()
        
        # For backward compatibility, we'll keep these columns in their standardized format
        # without renaming them. This is the key fix to prevent duplicate columns.
        
        # Load extraction history
        history_df = pd.read_sql_query("SELECT * FROM extraction_history ORDER BY timestamp DESC", conn)
        history = []
        
        # Convert DataFrame rows to dictionaries
        for _, row in history_df.iterrows():
            history_entry = {
                'filename': row['filename'],
                'timestamp': row['timestamp'],
                'extraction_method': row['extraction_method'],
                'success': bool(row['success'])
            }
            
            # Parse JSON fields
            if 'fields_extracted' in row and row['fields_extracted']:
                try:
                    history_entry['fields_extracted'] = json.loads(row['fields_extracted'])
                except (json.JSONDecodeError, TypeError):
                    history_entry['fields_extracted'] = {}
            
            if 'additional_info' in row and row['additional_info']:
                try:
                    history_entry['additional_info'] = json.loads(row['additional_info'])
                except (json.JSONDecodeError, TypeError):
                    history_entry['additional_info'] = {}
            
            history.append(history_entry)
        
        conn.close()
        
        return df, history
    except Exception as e:
        print(f"Error loading from database: {e}")
        return None, []

def add_extraction_to_history(
    filename: str, 
    extraction_method: str, 
    success: bool, 
    fields_extracted: Dict = None,
    additional_info: Dict = None
) -> Tuple[bool, str]:
    """
    Add a new extraction entry to the history.
    
    Args:
        filename: The name of the extracted file
        extraction_method: The method used for extraction
        success: Whether the extraction was successful
        fields_extracted: Dictionary of extracted fields
        additional_info: Any additional information to store
        
    Returns:
        Tuple[bool, str]: A tuple of (success, message)
    """
    try:
        conn = get_connection()
        
        # Convert dictionaries to JSON strings
        fields_json = json.dumps(fields_extracted or {})
        additional_json = json.dumps(additional_info or {})
        
        # Get current timestamp
        import datetime
        timestamp = datetime.datetime.now().isoformat()
        
        # Insert history entry
        conn.execute('''
        INSERT INTO extraction_history 
        (filename, timestamp, extraction_method, success, fields_extracted, additional_info)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            filename,
            timestamp,
            extraction_method,
            1 if success else 0,
            fields_json,
            additional_json
        ))
        
        conn.commit()
        conn.close()
        
        return True, "Extraction history updated successfully"
    except Exception as e:
        error_message = f"Error updating extraction history: {e}"
        print(error_message)
        return False, error_message

def get_extraction_history(limit: int = 100) -> List[Dict]:
    """
    Get the most recent extraction history entries.
    
    Args:
        limit: Maximum number of entries to return
        
    Returns:
        List[Dict]: List of extraction history entries
    """
    try:
        conn = get_connection()
        
        # Query the most recent entries
        cursor = conn.execute('''
        SELECT filename, timestamp, extraction_method, success, fields_extracted, additional_info
        FROM extraction_history
        ORDER BY timestamp DESC
        LIMIT ?
        ''', (limit,))
        
        history = []
        for row in cursor:
            # Parse JSON fields
            fields_extracted = {}
            additional_info = {}
            
            if row[4]:  # fields_extracted
                try:
                    fields_extracted = json.loads(row[4])
                except (json.JSONDecodeError, TypeError):
                    pass
            
            if row[5]:  # additional_info
                try:
                    additional_info = json.loads(row[5])
                except (json.JSONDecodeError, TypeError):
                    pass
            
            history.append({
                'filename': row[0],
                'timestamp': row[1],
                'extraction_method': row[2],
                'success': bool(row[3]),
                'fields_extracted': fields_extracted,
                'additional_info': additional_info
            })
        
        conn.close()
        return history
    except Exception as e:
        print(f"Error getting extraction history: {e}")
        return []

# Initialize the database when the module is imported
initialize_database()