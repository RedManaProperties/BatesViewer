import streamlit as st
import pandas as pd
from io import StringIO
import re
import csv

# The delimiter used in your Bates file format
DELIMITER = 'þ'

# The definitive list of 28 core column headers, in the correct order.
DEFINITIVE_HEADERS = [
    'Bates Begin', 
    'Bates End', 
    'Bates Begin Attach', 
    'Bates End Attach', 
    'Attachment Document', 
    'Pages', 
    'Author', 
    'Custodian/Source', 
    'Date Created', 
    'Date Last Modified', 
    'Date Received', 
    'Date Sent', 
    'Time Sent', 
    'Document Extension', 
    'Email BCC', 
    'Email CC', 
    'Email From', 
    'Email Subject/Title', 
    'Email To', 
    'Original Filename', 
    'File Size', 
    'Original Folder Path', 
    'MD5 Hash', 
    'Parent Document ID', 
    'Document Title', 
    'Time Zone', 
    'Text Link', 
    'Native Link' 
]

def clean_and_load_data(uploaded_file):
    """
    Reads the file line-by-line, uses the csv module to split on the explicit delimiter, 
    and manually constructs the DataFrame using the definitive column order.
    """
    try:
        # 1. Read and prepare content
        file_content = uploaded_file.getvalue().decode('utf-8')
        
        # Remove Byte Order Mark (BOM) and non-standard separator \x14 globally
        file_content = file_content.lstrip('\ufeff').replace('\x14', '')
        
        lines = file_content.split('\n')
        data_lines = [line.strip() for line in lines if line.strip()]

        if len(data_lines) < 4:
             # We expect at least the header (3 lines) and one data row (1 line)
             raise Exception("File content is too short to contain header and data.")

        # The header spans the first 3 rows in the original display due to newline in "Original\nFolder Path"
        # We need to find the index where actual data starts (after the multiline header)
        data_start_index = 0
        for i, line in enumerate(data_lines):
            if 'Native Link' in line:
                data_start_index = i + 1
                break
        
        # 2. Process Data Rows using the csv module for reliable splitting
        parsed_data = []
        expected_len = len(DEFINITIVE_HEADERS)
        
        # Use csv.reader with the custom delimiter for field splitting
        reader = csv.reader(data_lines[data_start_index:], delimiter=DELIMITER)
        
        for row_values in reader:
            # The split operation will create empty strings at the start/end due to the bounding 'þ'
            # and between consecutive 'þþ' delimiters for empty fields.
            
            # Filter empty strings at the start/end of the list that result from the leading/trailing delimiter
            cleaned_row = [v.strip() for v in row_values]
            
            if cleaned_row and cleaned_row[0] == '':
                cleaned_row.pop(0)
            if cleaned_row and cleaned_row[-1] == '':
                cleaned_row.pop(-1)
            
            current_len = len(cleaned_row)
            
            # Force the row to match the expected number of columns (31 total fields in original)
            if current_len > expected_len:
                cleaned_row = cleaned_row[:expected_len]
            elif current_len < expected_len:
                cleaned_row.extend([""] * (expected_len - current_len))

            if len(cleaned_row) == expected_len:
                parsed_data.append(cleaned_row)
        
        # 3. Create DataFrame and clean for final display
        df = pd.DataFrame(parsed_data, columns=DEFINITIVE_HEADERS)
        
        return df

    except Exception as e:
        st.error(f"An unexpected error occurred during parsing: {e}")
        return None

# --- Streamlit UI ---
st.set_page_config(layout="wide")

st.title("📂 Bates File Viewer")
st.markdown("Upload your structured Bates `.dat` file to convert the metadata into a readable, searchable table.")

uploaded_file = st.file_uploader("Choose a .dat or delimited file", type=['dat', 'txt', 'csv'])

if uploaded_file is not None:
    # Use the parsing function
    df = clean_and_load_data(uploaded_file)

    if df is not None and not df.empty:
        st.success("File successfully parsed and loaded! Data should now be in the correct order.")
        
        # Data Cleaning for Presentation
        if 'Pages' in df.columns:
            # Convert 'Pages' to numeric, filling non-numeric with empty string
            df['Pages'] = pd.to_numeric(df['Pages'], errors='coerce').fillna('').astype(object)
            
        # Drop columns that are entirely empty across all rows (common to keep only populated metadata)
        df = df.dropna(axis=1, how='all')

        # Display the interactive table, using the correct 'width' parameter
        st.dataframe(df, width='stretch')
        
        # Offer option to download the clean table as a CSV
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Clean Data as CSV",
            data=csv_data,
            file_name='parsed_bates_data.csv',
            mime='text/csv',
        )
    elif df is not None and df.empty:
        st.warning("The file was processed, but no data rows were found. Check if the file contains only the header.")
