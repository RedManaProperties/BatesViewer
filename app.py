import streamlit as st
import pandas as pd
from io import StringIO
import re

# The delimiter used in your Bates file format
DELIMITER = 'þ'

# The definitive list of ALL 31 column headers, including those that are often empty.
# We must include the "hidden" columns to maintain alignment for the actual data.
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
    'Native Link',
    # Note: The original file actually had 28 columns visible in the metadata provided, 
    # but sometimes the software outputs extra blank columns. Sticking to 28 based on the input text.
]
# However, the raw headers contained more columns and spaces between them.
# After experimentation, forcing a consistent 28-column split and using the standard columns is the best bet.

def parse_data_from_content(file_content):
    """Parses the content line-by-line using the fixed header list."""
    # Remove BOM and non-standard separator globally
    file_content = file_content.lstrip('\ufeff').replace('\x14', '')
    
    # Use a cleaner representation of the data for line-by-line processing
    lines = file_content.split('\n')
    
    # Find the start of the actual data rows
    data_start_index = 0
    for i, line in enumerate(lines):
        if 'Native Link' in line:
            data_start_index = i + 1
            break
            
    # Process only the data lines
    parsed_data = []
    
    for line in lines[data_start_index:]:
        if not line.strip():
            continue
            
        # Split every line by the delimiter 'þ', keeping empty strings for alignment
        # The split operation produces ['', Col1, Col2, Col3, ''] 
        row_values = [v.strip() for v in line.split(DELIMITER)]
        
        # Remove the mandatory empty strings that result from the leading and trailing delimiter
        if row_values and row_values[0] == '':
            row_values.pop(0)
        if row_values and row_values[-1] == '':
            row_values.pop(-1)

        # Ensure the row has exactly the correct number of fields (28) by padding or trimming
        expected_len = len(DEFINITIVE_HEADERS)
        current_len = len(row_values)
        
        if current_len > expected_len:
            row_values = row_values[:expected_len]
        elif current_len < expected_len:
            row_values.extend([""] * (expected_len - current_len))

        if len(row_values) == expected_len:
            parsed_data.append(row_values)
            
    # Create the DataFrame and enforce the correct column names for order
    df = pd.DataFrame(parsed_data, columns=DEFINITIVE_HEADERS)
    return df

def clean_and_load_data(uploaded_file):
    try:
        file_content = uploaded_file.getvalue().decode('utf-8')
        df = parse_data_from_content(file_content)
        
        # Data Cleaning for Presentation
        if 'Pages' in df.columns:
            # Convert 'Pages' to numeric, filling non-numeric with empty string
            df['Pages'] = pd.to_numeric(df['Pages'], errors='coerce').fillna('').astype(object)
            
        # Drop columns that are entirely empty across all rows 
        # (This is safe now that alignment is fixed)
        df = df.dropna(axis=1, how='all')
        
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
    df = clean_and_load_data(uploaded_file)

    if df is not None and not df.empty:
        st.success("File successfully parsed and loaded! Columns should now be aligned correctly.")
        
        # Display the interactive table, using the corrected 'width' parameter
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
        st.warning("The file was processed, but no data rows were found.")
