import streamlit as st
import pandas as pd
import numpy as np
import os
import tempfile
from datetime import datetime
import base64
import io
import json

from sds_extractor import extract_sds_data, get_sections
from data_processor import process_dataframe, filter_dataframe, generate_excel, generate_csv
from ocr_handler import is_scanned_pdf, process_ocr
from utils import read_pdf_text, display_pdf, save_dataframe, load_dataframe
from ai_extractor import extract_with_ai, extract_from_pdf_with_ai, get_api_status
# Import new ML extraction capabilities
from ml_extractor import (
    extract_sds_with_ml, 
    extract_from_pdf_with_ml, 
    get_ml_extraction_strategies, 
    get_available_ml_models
)
from db_handler import get_extraction_history, initialize_database, add_extraction_to_history

# Set page configuration
st.set_page_config(
    page_title="SDS Data Extractor",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Create a data directory if it doesn't exist
if not os.path.exists('data'):
    os.makedirs('data')

# Initialize the database
db_success, db_message = initialize_database()
if not db_success:
    st.error(f"Failed to initialize database: {db_message}")

# Load saved data if available
loaded_df, loaded_history = load_dataframe()

# Initialize session state variables
if 'sds_data' not in st.session_state:
    if loaded_df is not None:
        st.session_state.sds_data = loaded_df
    else:
        st.session_state.sds_data = pd.DataFrame(columns=[
            'Number', 'Product Name', 'Supplier/Manufacturer', 'Hazards', 'Location', 
            'SDS Available', 'Issue Date', 'Health Hazards', 'Health Category',
            'Physical Hazards', 'Physical Category', 'Hazardous Substance', 'Flash Point (Deg C)',
            'Dangerous Goods Class', 'Description', 'Packing Group', 'Appearance', 'Colour', 'Odour',
            'Last Updated Date', 'Source File'
        ])

if 'extraction_history' not in st.session_state:
    if loaded_history:
        st.session_state.extraction_history = loaded_history
    else:
        st.session_state.extraction_history = []

# Flag to track if data needs to be saved
if 'data_changed' not in st.session_state:
    st.session_state.data_changed = True

# Header
st.title("Safety Data Sheet (SDS) Extraction Tool")
st.markdown("""
This application extracts key information from Safety Data Sheets (SDS) in PDF format 
and creates a structured register for easy management and reporting.
""")

# Sidebar
with st.sidebar:
    st.header("Controls")
    
    # Show data location information
    with st.expander("📁 Data Storage Info", expanded=True):
        st.markdown("""
        **Data Storage:**
        - Primary storage: SQLite database (`./data/sds_database.sqlite`)
        - Backup: CSV file (`./data/sds_register.csv`)
        
        Data is automatically saved when you:
        - Add new SDS extractions
        - Update records
        - Delete records
        """)
        
        # Always show download buttons
        # For register data - get fresh from database
        if st.session_state.sds_data is not None and not st.session_state.sds_data.empty:
            # Generate CSV data from current dataframe 
            csv_buffer = io.StringIO()
            st.session_state.sds_data.to_csv(csv_buffer, index=False)
            csv_data = csv_buffer.getvalue().encode()
        else:
            # Create empty CSV with headers if dataframe is empty
            headers = "Number,Product Name,Supplier/Manufacturer,Hazards,Location,SDS Available,Issue Date,Health Hazards,Health Category,Physical Hazards,Physical Category,Hazardous Substance,Flash Point (Deg C),Dangerous Goods Class,Description,Packing Group,Appearance,Colour,Odour,Last Updated Date,Source File\n"
            csv_data = headers.encode()
        
        st.download_button(
            label="⬇️ Download Register CSV",
            data=csv_data,
            file_name="sds_register.csv",
            mime="text/csv",
            help="Download the SDS register data as a CSV file"
        )
        
        # For extraction history - get fresh from database
        if st.session_state.extraction_history:
            # Convert extraction history to JSON
            json_data = json.dumps(st.session_state.extraction_history, indent=2).encode()
        else:
            # Get history directly from database
            db_history = get_extraction_history(limit=100)
            json_data = json.dumps(db_history, indent=2).encode()
            
            # If still empty, create an empty array
            if not db_history:
                json_data = '[]'.encode()
        
        st.download_button(
            label="⬇️ Download History JSON",
            data=json_data,
            file_name="extraction_history.json",
            mime="application/json",
            help="Download the extraction history as a JSON file"
        )
    
    app_mode = st.radio(
        "Choose Operation Mode:",
        ["Upload & Extract", "View & Edit Register", "Generate Reports"]
    )
    
    if app_mode == "Upload & Extract":
        st.subheader("Upload Settings")
        extraction_method = st.radio(
            "Extraction Method:",
            ["Automatic", "Pattern-based", "Section-based", "AI-powered", "Advanced ML"]
        )
        
        # Show AI service status if AI-powered or Advanced ML is selected
        if extraction_method in ["AI-powered", "Advanced ML"]:
            api_status = get_api_status()
            ai_status_container = st.container()
            
            with ai_status_container:
                if api_status["openai_available"] or api_status["anthropic_available"]:
                    st.success(f"Using {api_status['active_service']} for {extraction_method} extraction")
                    
                    # Show ML extraction strategy options if Advanced ML is selected
                    if extraction_method == "Advanced ML":
                        ml_strategies = get_ml_extraction_strategies()
                        ml_strategy = st.selectbox(
                            "ML Extraction Strategy:",
                            ml_strategies,
                            index=ml_strategies.index("multi_pass_extraction") if "multi_pass_extraction" in ml_strategies else 0,
                            help="Choose an advanced extraction strategy for better results"
                        )
                        
                        # Show explanation of the selected strategy
                        strategy_descriptions = {
                            "direct_extraction": "Basic extraction using the latest AI model.",
                            "hierarchical_extraction": "First identifies document sections, then extracts from each section separately for better accuracy.",
                            "specialized_extraction": "Uses dedicated extraction approaches for each information type (hazards, first aid, etc.).",
                            "multi_pass_extraction": "Combines multiple extraction approaches and consolidates the best results (recommended)."
                        }
                        
                        if ml_strategy in strategy_descriptions:
                            st.info(f"**{ml_strategy}**: {strategy_descriptions[ml_strategy]}")
                else:
                    st.warning("No active AI API keys configured. Using enhanced pattern matching instead.")
                    st.info("The application will use sophisticated pattern matching algorithms. If you want to use AI extraction in the future, add an OpenAI or Anthropic API key.")
                    with st.expander("How to add API keys"):
                        st.markdown("""
                        To enable AI-powered extraction, add one of these API keys:
                        
                        1. **OpenAI API Key**: Get from [OpenAI](https://platform.openai.com/)
                        2. **Anthropic API Key**: Get from [Anthropic](https://console.anthropic.com/)
                        
                        Contact your administrator to add these as environment variables.
                        """)
        
        enable_ocr = st.checkbox("Enable OCR for scanned documents", value=True)
        process_all_pages = st.checkbox("Process all pages", value=True)
        
        if not process_all_pages:
            page_range = st.text_input("Page range (e.g., 1-5):", "1-5")
        
        st.markdown("---")
        st.subheader("Bulk Processing")
        bulk_process = st.checkbox("Enable bulk processing", value=False)
    
    elif app_mode == "View & Edit Register":
        st.subheader("Filter Options")
        
        if not st.session_state.sds_data.empty:
            columns = st.session_state.sds_data.columns.tolist()
            filter_column = st.selectbox("Filter by column:", columns)
            
            if filter_column in st.session_state.sds_data.columns:
                unique_values = st.session_state.sds_data[filter_column].dropna().unique().tolist()
                filter_value = st.selectbox("Select value:", ["All"] + unique_values)
        
        st.markdown("---")
        st.subheader("Actions")
        delete_all = st.button("Clear All Data")
        
        if delete_all:
            st.session_state.sds_data = pd.DataFrame(columns=[
                'Number', 'Product Name', 'Supplier/Manufacturer', 'Hazards', 'Location', 
                'SDS Available', 'Issue Date', 'Health Hazards', 'Health Category',
                'Physical Hazards', 'Physical Category', 'Hazardous Substance', 'Flash Point (Deg C)',
                'Dangerous Goods Class', 'Description', 'Packing Group', 'Appearance', 'Colour', 'Odour',
                'Last Updated Date', 'Source File'
            ])
            st.session_state.extraction_history = []
            
            # Save the empty data to file (to clear the saved data)
            save_success, save_message = save_dataframe(st.session_state.sds_data, st.session_state.extraction_history)
            
            if save_success:
                st.success(f"All data has been cleared from memory and storage!\n{save_message}")
            else:
                st.warning(f"Data cleared from memory but failed to clear saved data file. Error: {save_message}")
            
            st.rerun()
    
    elif app_mode == "Generate Reports":
        # Initialize session state for template clearing option if not already done
        if 'clear_template_option' not in st.session_state:
            st.session_state.clear_template_option = True
            
        # Add Excel export options with prominent checkbox
        st.subheader("Excel Export Options")
        st.session_state.clear_template_option = st.checkbox(
            "✅ Clear existing data in template (keep only headers)", 
            value=st.session_state.clear_template_option,
            help="When checked, Excel exports will place data starting from column A instead of columns Y/Z/AA"
        )
        
        st.subheader("Report Format")
        report_format = st.radio("Select format:", ["Excel", "CSV"])
        
        custom_columns = st.checkbox("Select specific columns", value=False)
        
        if custom_columns and not st.session_state.sds_data.empty:
            available_columns = st.session_state.sds_data.columns.tolist()
            selected_columns = st.multiselect(
                "Choose columns to include:", 
                available_columns,
                default=available_columns
            )
        
        st.markdown("---")
        st.subheader("Download")
        generate_report = st.button("Generate Report")

# Main content area
if app_mode == "Upload & Extract":
    col1, col2 = st.columns([3, 1])
    with col1:
        st.header("Upload SDS Documents")
    with col2:
        # Add export options header
        st.markdown("### 📊 Export Options")
        
        # Prepare file data for download buttons
        if os.path.exists('data/sds_register.csv'):
            with open('data/sds_register.csv', 'rb') as f:
                csv_data = f.read()
        else:
            # Create empty CSV with headers if it doesn't exist
            headers = 'Number,Product Name,Supplier/Manufacturer,Hazards,Location,SDS Available,Issue Date,Health Hazards,Health Category,Physical Hazards,Physical Category,Hazardous Substance,Flash Point (Deg C),Dangerous Goods Class,Description,Packing Group,Appearance,Colour,Odour,Last Updated Date,Source File\n'
            csv_data = headers.encode()
            
            # Also save it to disk
            os.makedirs('data', exist_ok=True)
            with open('data/sds_register.csv', 'wb') as f:
                f.write(csv_data)
        
        # Add buttons for both formats
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="⬇️ Download as CSV",
                data=csv_data,
                file_name="sds_register.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            # Create Excel file using session state option
            if 'sds_data' in st.session_state and not st.session_state.sds_data.empty:
                # Create a clean copy of the dataframe for processing
                export_df = st.session_state.sds_data.copy()
                
                # Pre-process complex data types to convert them to string format
                for col in export_df.columns:
                    export_df[col] = export_df[col].apply(lambda x: 
                                                str(x) if isinstance(x, dict) else
                                                '; '.join([str(i) for i in x]) if isinstance(x, list) else x)
                
                excel_data = generate_excel(export_df)
                st.download_button(
                    label="⬇️ Download as Excel",
                    data=excel_data.getvalue(),
                    file_name="sds_register.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
    
    if bulk_process:
        uploaded_files = st.file_uploader("Upload multiple SDS PDFs", type="pdf", accept_multiple_files=True)
        
        if uploaded_files and st.button("Process All Files"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Track successful and failed files
            successful_files = []
            failed_files = []
            
            for i, uploaded_file in enumerate(uploaded_files):
                file_progress = (i) / len(uploaded_files)
                progress_bar.progress(file_progress)
                status_text.text(f"Processing file {i+1} of {len(uploaded_files)}: {uploaded_file.name}")
                
                # Create a temporary file to store the PDF
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                try:
                    # Determine if OCR is needed
                    needs_ocr = is_scanned_pdf(tmp_path) if enable_ocr else False
                    
                    # Get text from PDF
                    if needs_ocr:
                        pdf_text = process_ocr(tmp_path)
                    else:
                        pdf_text = read_pdf_text(tmp_path)
                    
                    # Extract data based on the selected method
                    if extraction_method == "AI-powered":
                        # Check if AI APIs are available
                        api_status = get_api_status()
                        if api_status["openai_available"] or api_status["anthropic_available"]:
                            # Attempt AI-powered extraction with light mode fallback for rate limits
                            try:
                                with st.spinner("Extracting data with AI (this may take a moment)..."):
                                    # Try with light mode to reduce API calls
                                    extracted_data = extract_with_ai(pdf_text, uploaded_file.name, light_mode=True)
                                    
                                    # Check for errors in the response
                                    if "error" in extracted_data:
                                        error_msg = extracted_data["error"]
                                        if "rate limit" in error_msg.lower() or "429" in error_msg:
                                            st.warning("API rate limit detected. Using pattern-based extraction as fallback.")
                                            # Fall back to pattern-based extraction
                                            extracted_data = extract_sds_data(pdf_text, "Pattern-based")
                                            st.info("Data extracted using fallback method.")
                            except Exception as e:
                                st.warning(f"AI extraction error: {str(e)}. Falling back to pattern-based extraction.")
                                extracted_data = extract_sds_data(pdf_text, "Pattern-based")
                        else:
                            # Fallback to automatic extraction if no API keys available
                            st.warning("No AI API keys found. Falling back to automatic extraction.")
                            extracted_data = extract_sds_data(pdf_text, "Automatic")
                    elif extraction_method == "Advanced ML":
                        # Check if AI APIs are available
                        api_status = get_api_status()
                        if api_status["openai_available"] or api_status["anthropic_available"]:
                            # Use advanced ML extraction with selected strategy and light mode
                            try:
                                with st.spinner("Extracting data with Advanced ML (this may take a moment)..."):
                                    # Add debug logging
                                    print("DEBUG: Starting Advanced ML extraction")
                                    if 'ml_strategy' in locals():
                                        print(f"DEBUG: Using ML strategy: {ml_strategy}")
                                        # Use light mode to reduce API calls
                                        try:
                                            extracted_data = extract_sds_with_ml(pdf_text, ml_strategy, light_mode=True)
                                            print(f"DEBUG: ML extraction complete, data keys: {list(extracted_data.keys())}")
                                        except Exception as e:
                                            print(f"DEBUG: Error in ML extraction: {str(e)}")
                                            st.error(f"ML extraction error: {str(e)}")
                                            extracted_data = {"error": f"Extraction failed: {str(e)}"}
                                    else:
                                        print("DEBUG: No ML strategy specified, using direct_extraction")
                                        # Default to direct_extraction as it uses fewer API calls
                                        try:
                                            extracted_data = extract_sds_with_ml(pdf_text, "direct_extraction", light_mode=True)
                                            print(f"DEBUG: ML extraction complete, data keys: {list(extracted_data.keys())}")
                                        except Exception as e:
                                            print(f"DEBUG: Error in ML extraction: {str(e)}")
                                            st.error(f"ML extraction error: {str(e)}")
                                            extracted_data = {"error": f"Extraction failed: {str(e)}"}
                                    
                                    # Check for errors in the response
                                    if "error" in extracted_data:
                                        error_msg = extracted_data["error"]
                                        if "rate limit" in error_msg.lower() or "429" in error_msg:
                                            st.warning("API rate limit detected. Using pattern-based extraction as fallback.")
                                            # Fall back to pattern-based extraction
                                            extracted_data = extract_sds_data(pdf_text, "Pattern-based")
                                            st.info("Data extracted using fallback method.")
                            except Exception as e:
                                st.warning(f"ML extraction error: {str(e)}. Falling back to pattern-based extraction.")
                                extracted_data = extract_sds_data(pdf_text, "Pattern-based")
                        else:
                            # Fallback to automatic extraction if no API keys available
                            st.warning("No AI API keys found. Falling back to automatic extraction.")
                            extracted_data = extract_sds_data(pdf_text, "Automatic")
                    else:
                        # Use regular pattern-based extraction
                        extracted_data = extract_sds_data(pdf_text, extraction_method)
                    
                    # Add source file and timestamp
                    extracted_data['Source File'] = uploaded_file.name
                    extracted_data['Last Updated Date'] = datetime.now().strftime('%Y-%m-%d')
                    
                    # Append to the dataframe
                    st.session_state.sds_data = pd.concat([
                        st.session_state.sds_data, 
                        pd.DataFrame([extracted_data])
                    ], ignore_index=True)
                    
                    # Log the extraction
                    extraction_log = {
                        'filename': uploaded_file.name,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'extraction_method': extraction_method,
                        'success': True,
                        'fields_extracted': extracted_data
                    }
                    
                    # Add to session state
                    st.session_state.extraction_history.append(extraction_log)
                    
                    # Log directly to database
                    add_extraction_to_history(
                        filename=uploaded_file.name,
                        extraction_method=extraction_method,
                        success=True,
                        fields_extracted=extracted_data
                    )
                    
                    # Track successful file
                    successful_files.append(extracted_data['Product Name'] or uploaded_file.name)
                    
                    # Mark data as changed
                    st.session_state.data_changed = True
                    
                except Exception as e:
                    error_msg = str(e)
                    failed_files.append(f"{uploaded_file.name} (Error: {error_msg})")
                    
                    # Add failed extraction to history
                    extraction_log = {
                        'filename': uploaded_file.name,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'extraction_method': extraction_method,
                        'success': False,
                        'error': error_msg
                    }
                    
                    # Add to session state
                    st.session_state.extraction_history.append(extraction_log)
                    
                    # Log directly to database
                    add_extraction_to_history(
                        filename=uploaded_file.name,
                        extraction_method=extraction_method,
                        success=False,
                        additional_info={'error': error_msg}
                    )
                
                # Clean up the temporary file
                os.unlink(tmp_path)
            
            progress_bar.progress(1.0)
            status_text.text("Processing complete!")
            
            try:
                # Save all processed data to file - always try to save
                save_success, save_message = save_dataframe(st.session_state.sds_data, st.session_state.extraction_history)
                
                # Show detailed results
                st.success(f"✅ Processed {len(uploaded_files)} files: {len(successful_files)} successful, {len(failed_files)} failed")
                
                # Print status for debugging
                st.write(f"DataFrame shape after bulk processing: {st.session_state.sds_data.shape}")
                
                if successful_files:
                    with st.expander("Successfully processed files", expanded=True):
                        for i, name in enumerate(successful_files):
                            st.write(f"{i+1}. {name}")
                
                if failed_files:
                    with st.expander("Failed files", expanded=True):
                        for i, error in enumerate(failed_files):
                            st.write(f"{i+1}. {error}")
                
                if save_success:
                    st.info(f"Data saved to register: {save_message}")
                    
                    # Show the DataFrame to confirm contents
                    st.subheader("Current Register Data")
                    st.dataframe(st.session_state.sds_data.head(10), use_container_width=True)
                else:
                    st.warning(f"Data added to register but failed to save to file. Error: {save_message}")
                
                # Add download button right after processing - directly from the database/session
                # Generate CSV directly from dataframe
                csv_buffer = io.StringIO()
                st.session_state.sds_data.to_csv(csv_buffer, index=False)
                csv_data = csv_buffer.getvalue().encode()
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.download_button(
                        label="⬇️ Download Register as CSV",
                        data=csv_data,
                        file_name="sds_register.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col2:
                    # Generate Excel version directly from dataframe
                    # Create a clean copy of the dataframe for processing
                    export_df = st.session_state.sds_data.copy()
                    
                    # Pre-process complex data types to convert them to string format
                    for col in export_df.columns:
                        export_df[col] = export_df[col].apply(lambda x: 
                                                    str(x) if isinstance(x, dict) else
                                                    '; '.join([str(i) for i in x]) if isinstance(x, list) else x)
                    
                    output = generate_excel(export_df)
                    st.download_button(
                        label="⬇️ Download Register as Excel",
                        data=output.getvalue(),
                        file_name="sds_register.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            except Exception as e:
                st.error(f"Error saving bulk processed data: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
    
    else:
        uploaded_file = st.file_uploader("Upload SDS PDF", type="pdf")
        
        if uploaded_file:
            # Display the PDF
            st.subheader("Uploaded Document")
            pdf_display = display_pdf(uploaded_file)
            st.markdown(pdf_display, unsafe_allow_html=True)
            
            if st.button("Extract Data"):
                with st.spinner("Extracting data from the document..."):
                    # Create a temporary file to store the PDF
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_path = tmp_file.name
                    
                    try:
                        # Determine if OCR is needed
                        needs_ocr = is_scanned_pdf(tmp_path) if enable_ocr else False
                        
                        # Get text from PDF
                        if needs_ocr:
                            pdf_text = process_ocr(tmp_path)
                            st.info("Document was processed using OCR.")
                        else:
                            pdf_text = read_pdf_text(tmp_path)
                        
                        # Extract data based on the selected method
                        if extraction_method == "AI-powered":
                            # Check if AI APIs are available
                            api_status = get_api_status()
                            if api_status["openai_available"] or api_status["anthropic_available"]:
                                try:
                                    # Use AI-powered extraction
                                    extracted_data = extract_with_ai(pdf_text, uploaded_file.name)
                                    
                                    # Add source file and timestamp immediately
                                    extracted_data['Source File'] = uploaded_file.name
                                    extracted_data['Last Updated Date'] = datetime.now().strftime('%Y-%m-%d')
                                    
                                    st.success(f"Extraction performed using {api_status['active_service']} AI")
                                    
                                    # Auto-save the AI extraction by default
                                    st.info("AI extracted data will be saved to the register automatically")
                                    
                                    # Directly save to the dataframe
                                    # Create a DataFrame with a single row for this extraction
                                    new_row_df = pd.DataFrame([extracted_data])
                                    
                                    # Append to the dataframe
                                    if st.session_state.sds_data.empty:
                                        st.session_state.sds_data = new_row_df
                                    else:
                                        st.session_state.sds_data = pd.concat([
                                            st.session_state.sds_data, 
                                            new_row_df
                                        ], ignore_index=True)
                                    
                                    # Log the extraction
                                    st.session_state.extraction_history.append({
                                        'filename': uploaded_file.name,
                                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                        'status': 'Success (AI extraction)'
                                    })
                                    
                                    # Save the data to file immediately
                                    save_success, save_message = save_dataframe(st.session_state.sds_data, st.session_state.extraction_history)
                                    
                                    if save_success:
                                        st.success(f"✅ AI extraction automatically saved to register!\n{save_message}")
                                        
                                        # Show the current register with the new entry
                                        st.subheader("Current Register Data")
                                        st.dataframe(st.session_state.sds_data, use_container_width=True)
                                        
                                        # Add a download button for immediate download - direct from database
                                        # Generate CSV directly from dataframe
                                        csv_buffer = io.StringIO()
                                        st.session_state.sds_data.to_csv(csv_buffer, index=False)
                                        csv_data = csv_buffer.getvalue().encode()
                                            
                                        st.download_button(
                                            label="⬇️ Download Updated Register",
                                            data=csv_data,
                                            file_name="sds_register.csv",
                                            mime="text/csv"
                                        )
                                    else:
                                        st.warning(f"Failed to save AI extraction to file. Error: {save_message}")
                                        
                                except Exception as e:
                                    st.error(f"Error during AI extraction: {str(e)}")
                                    # Fallback to automatic extraction if AI fails
                                    st.warning("AI extraction failed. Falling back to automatic extraction.")
                                    extracted_data = extract_sds_data(pdf_text, "Automatic")
                            else:
                                # Fallback to automatic extraction if no API keys available
                                st.warning("No AI API keys found. Falling back to automatic extraction.")
                                extracted_data = extract_sds_data(pdf_text, "Automatic")
                        elif extraction_method == "Advanced ML":
                            # Check if AI APIs are available
                            api_status = get_api_status()
                            print(f"DEBUG: API Status = {api_status}")
                            if api_status["openai_available"] or api_status["anthropic_available"]:
                                try:
                                    # Use advanced ML extraction with selected strategy
                                    active_service = api_status.get('active_service', 'Unknown API')
                                    st.write(f"Using {active_service} for extraction...")
                                    
                                    # Create a placeholder for the extraction progress
                                    ml_status = st.empty()
                                    ml_status.info("Starting ML extraction...")
                                    
                                    if 'ml_strategy' in locals():
                                        ml_status.info(f"Using {ml_strategy} extraction strategy...")
                                        print(f"DEBUG: Calling extract_sds_with_ml with strategy={ml_strategy}")
                                        try:
                                            extracted_data = extract_sds_with_ml(pdf_text, ml_strategy, light_mode=True)
                                            print(f"DEBUG: ML extraction result keys: {list(extracted_data.keys())}")
                                        except Exception as ml_err:
                                            print(f"DEBUG: Error in extract_sds_with_ml: {str(ml_err)}")
                                            st.error(f"ML extraction error: {str(ml_err)}")
                                            # Fall back to AI extraction
                                            ml_status.warning("ML extraction failed, falling back to basic AI extraction...")
                                            extracted_data = extract_with_ai(pdf_text, light_mode=True)
                                    else:
                                        # Default to direct_extraction if no strategy selected (uses fewer API calls)
                                        ml_status.info("Using direct extraction strategy...")
                                        print("DEBUG: Using direct_extraction as no strategy was specified")
                                        try:
                                            extracted_data = extract_sds_with_ml(pdf_text, "direct_extraction", light_mode=True)
                                            print(f"DEBUG: ML extraction result keys: {list(extracted_data.keys())}")
                                        except Exception as ml_err:
                                            print(f"DEBUG: Error in extract_sds_with_ml: {str(ml_err)}")
                                            st.error(f"ML extraction error: {str(ml_err)}")
                                            # Fall back to AI extraction
                                            ml_status.warning("ML extraction failed, falling back to basic AI extraction...")
                                            extracted_data = extract_with_ai(pdf_text, light_mode=True)
                                    
                                    # Check if there was an error in the extraction
                                    if "error" in extracted_data:
                                        error_msg = extracted_data["error"]
                                        ml_status.warning(f"ML extraction returned an error: {error_msg}")
                                        print(f"DEBUG: ML extraction error from response: {error_msg}")
                                        # Fall back to AI extraction
                                        extracted_data = extract_with_ai(pdf_text, light_mode=True)
                                        ml_status.info("Using basic AI extraction as fallback...")
                                    else:
                                        ml_status.success("ML extraction completed successfully!")
                                    
                                    # Add source file and timestamp immediately
                                    extracted_data['Source File'] = uploaded_file.name
                                    extracted_data['Last Updated Date'] = datetime.now().strftime('%Y-%m-%d')
                                    
                                    st.success(f"Extraction performed using Advanced ML with {api_status['active_service']}")
                                    
                                    # Display extracted data summary
                                    with st.expander("Extracted Data Summary", expanded=True):
                                        st.write(f"Product Name: {extracted_data.get('Product Name', 'Not found')}")
                                        st.write(f"CAS Number: {extracted_data.get('CAS Number', 'Not found')}")
                                        st.write(f"Supplier: {extracted_data.get('Supplier/Manufacturer', 'Not found')}")
                                    
                                    # Auto-save the ML extraction by default
                                    st.info("ML extracted data will be saved to the register automatically")
                                    
                                    # Directly save to the dataframe
                                    new_row_df = pd.DataFrame([extracted_data])
                                    
                                    # Append to the dataframe
                                    if st.session_state.sds_data.empty:
                                        st.session_state.sds_data = new_row_df
                                    else:
                                        st.session_state.sds_data = pd.concat([
                                            st.session_state.sds_data, 
                                            new_row_df
                                        ], ignore_index=True)
                                    
                                    # Log the extraction with detailed method information
                                    extraction_method_detail = f"Advanced ML ({ml_strategy if 'ml_strategy' in locals() else 'multi_pass_extraction'})"
                                    st.session_state.extraction_history.append({
                                        'filename': uploaded_file.name,
                                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                        'extraction_method': extraction_method_detail,
                                        'success': True,
                                        'fields_extracted': extracted_data
                                    })
                                    
                                    # Log directly to database
                                    add_extraction_to_history(
                                        filename=uploaded_file.name,
                                        extraction_method=extraction_method_detail,
                                        success=True,
                                        fields_extracted=extracted_data
                                    )
                                    
                                    # Save to database
                                    save_success, save_message = save_dataframe(st.session_state.sds_data, st.session_state.extraction_history)
                                    st.session_state.data_changed = True
                                    
                                    # Display the extracted data
                                    st.subheader("Extracted Data")
                                    display_df = pd.DataFrame([extracted_data])
                                    st.dataframe(display_df, use_container_width=True)
                                    
                                    # Show confirmation if save successful
                                    if save_success:
                                        st.success(f"Advanced ML extraction saved to register: {save_message}")
                                        
                                        # Add a download button for the updated register
                                        csv_buffer = io.StringIO()
                                        st.session_state.sds_data.to_csv(csv_buffer, index=False)
                                        csv_data = csv_buffer.getvalue().encode()
                                            
                                        st.download_button(
                                            label="⬇️ Download Updated Register",
                                            data=csv_data,
                                            file_name="sds_register.csv",
                                            mime="text/csv"
                                        )
                                    else:
                                        st.warning(f"Failed to save ML extraction to file. Error: {save_message}")
                                except Exception as e:
                                    st.error(f"Advanced ML extraction failed: {str(e)}")
                                    # Fallback to automatic extraction if ML fails
                                    st.warning("ML extraction failed. Falling back to automatic extraction.")
                                    extracted_data = extract_sds_data(pdf_text, "Automatic")
                            else:
                                # Fallback to automatic extraction if no API keys available
                                st.warning("No AI API keys found. Falling back to automatic extraction.")
                                extracted_data = extract_sds_data(pdf_text, "Automatic")
                        else:
                            # Use regular pattern-based extraction
                            extracted_data = extract_sds_data(pdf_text, extraction_method)
                        
                        # Add source file and timestamp
                        extracted_data['Source File'] = uploaded_file.name
                        extracted_data['Last Updated Date'] = datetime.now().strftime('%Y-%m-%d')
                        
                        # Display extracted data with editable fields in a simpler form
                        st.subheader("Extracted Information")
                        edited_data = {}
                        
                        # Create copies of the extracted data for editing
                        for key, value in extracted_data.items():
                            if key != 'Source File' and key != 'Last Updated Date':
                                # Use a more unique key pattern to avoid conflicts
                                input_key = f"edit_{key}_{hash(uploaded_file.name)}"
                                edited_value = st.text_input(key, value, key=input_key)
                                edited_data[key] = edited_value
                            else:
                                edited_data[key] = value
                        
                        # Create a simple button instead of a form
                        if st.button("Save to Register", key=f"save_btn_{hash(uploaded_file.name)}"):
                            try:
                                # Create a DataFrame with a single row for this extraction
                                new_row_df = pd.DataFrame([edited_data])
                                
                                # Append to the dataframe
                                if st.session_state.sds_data.empty:
                                    st.session_state.sds_data = new_row_df
                                else:
                                    st.session_state.sds_data = pd.concat([
                                        st.session_state.sds_data, 
                                        new_row_df
                                    ], ignore_index=True)
                                
                                # Log the extraction
                                st.session_state.extraction_history.append({
                                    'filename': uploaded_file.name,
                                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    'status': 'Success'
                                })
                                
                                # Print status for debugging
                                st.write(f"DataFrame shape: {st.session_state.sds_data.shape}")
                                
                                # Save the data to file
                                save_success, save_message = save_dataframe(st.session_state.sds_data, st.session_state.extraction_history)
                                
                                if save_success:
                                    st.success(f"✅ Data saved to register and file successfully!\n{save_message}")
                                    
                                    # Show the first few rows of the dataframe to confirm
                                    st.subheader("Current Register Data")
                                    st.dataframe(st.session_state.sds_data, use_container_width=True)
                                    
                                    # Add a download button for immediate download - direct from database
                                    # Use our new custom CSV generator that starts data in column A
                                    # This properly reformats columns and places data at column A
                                    csv_buffer = generate_csv(st.session_state.sds_data)
                                    csv_data = csv_buffer.getvalue().encode()
                                        
                                    st.download_button(
                                        label="⬇️ Download Updated Register",
                                        data=csv_data,
                                        file_name="sds_register.csv",
                                        mime="text/csv"
                                    )
                                else:
                                    st.warning(f"Data saved to register but failed to save to file. Error: {save_message}")
                            except Exception as e:
                                st.error(f"Error saving data: {str(e)}")
                                import traceback
                                st.code(traceback.format_exc())
                        
                    except Exception as e:
                        st.error(f"Error during extraction: {str(e)}")
                        st.session_state.extraction_history.append({
                            'filename': uploaded_file.name,
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'status': f'Failed: {str(e)}'
                        })
                    
                    # Clean up the temporary file
                    os.unlink(tmp_path)

elif app_mode == "View & Edit Register":
    st.header("SDS Data Register")
    
    # Add direct download button at the top of the register view
    col1, col2 = st.columns([3, 1])
    with col2:
        # Always show download button - direct from database/session
        if st.session_state.sds_data is not None and not st.session_state.sds_data.empty:
            # Use our new custom CSV generator that starts data in column A
            # This properly reformats columns and places data at column A
            csv_buffer = generate_csv(st.session_state.sds_data)
            csv_data = csv_buffer.getvalue().encode()
        else:
            # Create empty CSV with headers if no data exists
            headers = 'Number,Product Name,Supplier/Manufacturer,Hazards,Location,SDS Available,Issue Date,Health Hazards,Health Category,Physical Hazards,Physical Category,Hazardous Substance,Flash Point (Deg C),Dangerous Goods Class,Description,Packing Group,Appearance,Colour,Odour,Last Updated Date,Source File\n'
            csv_data = headers.encode()
            
        st.download_button(
            label="⬇️ Download Register",
            data=csv_data,
            file_name="sds_register.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    if st.session_state.sds_data.empty:
        st.info("No data available. Please upload and extract SDS documents first.")
    else:
        # Apply filtering if specified
        if 'filter_column' in locals() and 'filter_value' in locals() and filter_value != "All":
            filtered_df = st.session_state.sds_data[st.session_state.sds_data[filter_column] == filter_value]
        else:
            filtered_df = st.session_state.sds_data
        
        # Show the dataframe
        st.dataframe(filtered_df, use_container_width=True)
        
        # Editing functionality
        st.subheader("Edit Record")
        if not filtered_df.empty:
            record_indices = filtered_df.index.tolist()
            # Check if 'Product Name' exists, otherwise use 'product_name' column
            product_name_col = 'Product Name' if 'Product Name' in filtered_df.columns else 'product_name'
            record_names = [f"{i}: {filtered_df.loc[i, product_name_col]}" for i in record_indices]
            selected_record = st.selectbox("Select record to edit:", record_names)
            
            if selected_record:
                record_idx = int(selected_record.split(":")[0])
                
                st.subheader(f"Editing: {filtered_df.loc[record_idx, product_name_col]}")
                
                edited_values = {}
                for column in filtered_df.columns:
                    if column not in ['Source File']:
                        current_value = filtered_df.loc[record_idx, column]
                        edited_value = st.text_input(f"{column}:", current_value, key=f"edit_{column}_{record_idx}")
                        edited_values[column] = edited_value
                
                if st.button("Update Record"):
                    for column, value in edited_values.items():
                        st.session_state.sds_data.loc[record_idx, column] = value
                    
                    # Save the updated data
                    save_success, save_message = save_dataframe(st.session_state.sds_data, st.session_state.extraction_history)
                    
                    if save_success:
                        st.success(f"Record updated and saved successfully!\n{save_message}")
                    else:
                        st.warning(f"Record updated but failed to save to file. Error: {save_message}")
                    
                    st.rerun()
                
                if st.button("Delete Record"):
                    st.session_state.sds_data = st.session_state.sds_data.drop(record_idx).reset_index(drop=True)
                    
                    # Save the updated data
                    save_success, save_message = save_dataframe(st.session_state.sds_data, st.session_state.extraction_history)
                    
                    if save_success:
                        st.success(f"Record deleted and saved successfully!\n{save_message}")
                    else:
                        st.warning(f"Record deleted but failed to save to file. Error: {save_message}")
                    
                    st.rerun()
    
    # Extraction History
    st.header("Extraction History")
    if st.session_state.extraction_history:
        history_df = pd.DataFrame(st.session_state.extraction_history)
        st.dataframe(history_df, use_container_width=True)
    else:
        st.info("No extraction history available.")

elif app_mode == "Generate Reports":
    st.header("Generate SDS Reports")
    
    # Add a title for export options section
    st.subheader("Export Options")
    st.markdown("---")
    
    # Always show download buttons at the top
    st.subheader("Quick Download")
    col1, col2 = st.columns(2)
    
    # Prepare CSV data - direct from database/session
    if st.session_state.sds_data is not None and not st.session_state.sds_data.empty:
        # Use our new custom CSV generator that starts data in column A
        # This properly reformats columns and places data at column A
        csv_buffer = generate_csv(st.session_state.sds_data)
        csv_data = csv_buffer.getvalue().encode()
    else:
        # Create empty CSV with headers if no data exists
        headers = 'Number,Product Name,Supplier/Manufacturer,Hazards,Location,SDS Available,Issue Date,Health Hazards,Health Category,Physical Hazards,Physical Category,Hazardous Substance,Flash Point (Deg C),Dangerous Goods Class,Description,Packing Group,Appearance,Colour,Odour,Last Updated Date,Source File\n'
        csv_data = headers.encode()
    
    with col1:
        st.download_button(
            label="⬇️ Download as CSV",
            data=csv_data,
            file_name="sds_register.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # For Excel, we need some data to create a valid Excel file
        if not st.session_state.sds_data.empty:
            # Generate Excel from session data if available
            output = generate_excel(st.session_state.sds_data)
        else:
            # Create an empty DataFrame with the correct columns
            empty_df = pd.DataFrame(columns=[
                'Product Name', 'CAS Number', 'Chemical Identification', 
                'Hazard Classification', 'Precautionary Statements', 
                'First Aid Measures', 'Supplier Information', 
                'Environmental Hazards', 'Regulatory Compliance Information',
                'Last Updated Date', 'Source File'
            ])
            output = generate_excel(empty_df)
            
        st.download_button(
            label="⬇️ Download as Excel",
            data=output.getvalue(),
            file_name="sds_register.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    st.markdown("---")
    
    if st.session_state.sds_data.empty:
        st.info("No data available. Please upload and extract SDS documents first.")
    else:
        # Display a preview of the data
        st.subheader("Data Preview")
        
        if 'selected_columns' in locals() and custom_columns:
            preview_df = st.session_state.sds_data[selected_columns]
        else:
            preview_df = st.session_state.sds_data
        
        st.dataframe(preview_df.head(5), use_container_width=True)
        
        # Generate the report if requested
        if 'generate_report' in locals() and generate_report:
            try:
                if 'selected_columns' in locals() and custom_columns:
                    export_df = st.session_state.sds_data[selected_columns]
                else:
                    export_df = st.session_state.sds_data
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                if report_format == "Excel":
                    # Generate Excel file
                    output = generate_excel(export_df)
                    file_name = f"SDS_Register_{timestamp}.xlsx"
                    
                    # Create a download button using Streamlit's download_button
                    st.download_button(
                        label="Download Excel File",
                        data=output.getvalue(),
                        file_name=file_name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                else:  # CSV
                    # Generate CSV file
                    output = generate_csv(export_df)
                    file_name = f"SDS_Register_{timestamp}.csv"
                    
                    # Create a download button using Streamlit's download_button
                    st.download_button(
                        label="Download CSV File",
                        data=output.getvalue(),
                        file_name=file_name,
                        mime="text/csv"
                    )
                
                st.success(f"Report generated successfully! Click the link above to download.")
            
            except Exception as e:
                st.error(f"Error generating report: {str(e)}")
