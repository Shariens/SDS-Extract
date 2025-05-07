import pandas as pd
import sys

def analyze_excel_template(file_path):
    """
    Analyze the Excel template to understand its structure and columns.
    """
    try:
        print(f"Attempting to read Excel file: {file_path}")
        # Try with different engines
        try:
            df = pd.read_excel(file_path, engine='openpyxl')
        except Exception as e1:
            print(f"Failed with openpyxl: {str(e1)}")
            try:
                df = pd.read_excel(file_path, engine='xlrd')
            except Exception as e2:
                print(f"Failed with xlrd: {str(e2)}")
                return
        
        # Display basic information
        print(f"\nExcel template has {df.shape[0]} rows and {df.shape[1]} columns")
        print("\nColumn list:")
        for idx, col in enumerate(df.columns):
            print(f"  {idx+1}. {col}")
        
        # Show a sample of the data (just a few rows)
        if not df.empty:
            print("\nSample data (first 2 rows):")
            sample = df.head(2)
            print(sample.to_string(index=False, max_colwidth=30))
            
            # Check for empty columns
            empty_cols = [col for col in df.columns if df[col].isna().all()]
            if empty_cols:
                print("\nEmpty columns found:")
                for col in empty_cols:
                    print(f"  - {col}")
            
            # Analyze data types
            print("\nColumn data types:")
            for col in df.columns:
                data_type = df[col].dtype
                non_null_count = df[col].count()
                print(f"  - {col}: {data_type} ({non_null_count}/{df.shape[0]} non-null values)")
        
    except Exception as e:
        print(f"Error analyzing Excel template: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_template.py <excel_file_path>")
        sys.exit(1)
    
    excel_file = sys.argv[1]
    analyze_excel_template(excel_file)