import streamlit as st
import pandas as pd
from io import StringIO
import re
import csv
import string

# The delimiter used in your Bates file format
DELIMITER = 'þ'

def generate_column_names(n):
    """Generates column names A, B, C, ..., AA, AB, etc."""
    names = []
    for i in range(n):
        name = ""
        # Handle columns beyond Z (e.g., AA, AB)
        while i >= 0:
            name = string.ascii_uppercase[i % 26] + name
            i = i // 26 - 1
        names.append(name)
    return names

def clean_and_load_data(uploaded_file):
    """
    Reads the file line-by-line, uses the csv module to split, 
    and determines the column headers based on the largest row width encountered.
    """
    try:
        # 1. Read and prepare content
        file_content = uploaded_file.getvalue().decode('utf-8')
        
        # Remove Byte Order Mark (BOM) and non-standard separator \x14 globally
        file_content = file_content.lstrip('\ufeff').replace('\x14', '')
        
        lines = file_content.split('\n')
        
        # Find the start of the actual data rows by looking for the last line of the header
        data_start_index = 0
        for i, line in enumerate(lines):
            if 'Native Link' in line:
                data_start_index = i + 1
                break
        
        # 2. Process Data Rows to determine maximum column width
        raw_data_lines = lines[data_start_index:]
        
        max_cols = 0
        all_data_rows = []
        
        # Use csv.reader for reliable splitting based on the delimiter
        reader = csv.reader(raw_data_lines, delimiter=DELIMITER)
        
        for row_values in reader:
            if not row_values:
                continue
                
            # Filter empty strings at the start/end of the list that result from the leading/trailing delimiter
            cleaned_row = [v.strip() for v in row_values]
            
            if cleaned_row and cleaned_row[0] == '':
                cleaned_row.pop(0)
            if cleaned_row and cleaned_row[-1] == '':
                cleaned_row.pop(-1)
            
            row_len = len(cleaned_row)
            
            # Track the widest row to define all headers
            if row_len > max_cols:
                max_cols = row_len
                
            all_data_rows.append(cleaned_row)
            
        if max_cols == 0:
            raise Exception("No columns detected or no data rows found.")

        # 3. Standardize and pad all rows to the maximum width
        for row in all_data_rows:
            if len(row) < max_cols:
                row.extend([""] * (max_cols - len(row)))
            # Truncation is unnecessary if max_cols is the max detected length
            
        # 4. Create Generic Headers
        generic_headers = generate_column_names(max_cols)

        # 5. Create DataFrame
        df = pd.DataFrame(all_data_rows, columns=generic_headers)
        
        return df

    except Exception as e:
        st.error(f"An unexpected error occurred during parsing: {e}")
        return None

# --- Streamlit UI ---
st.set_page_config(layout="wide")

st.title("📂 Bates File Viewer (Generic Headers)")
st.markdown("This view uses simple letter headers to ensure maximum column alignment. Inspect columns carefully to see data relationships.")

uploaded_file = st.file_uploader("Choose a .dat or delimited file", type=['dat', 'txt', 'csv'])

if uploaded_file is not None:
    df = clean_and_load_data(uploaded_file)

    if df is not None and not df.empty:
        st.success(f"File successfully parsed and loaded with {df.shape[1]} columns. Columns are aligned by delimiter position.")
        
        # Data Cleaning for Presentation (No explicit 'Pages' column name needed)
        
        # Drop columns that are entirely empty across all rows 
        # (Often necessary in Bates files to remove empty placeholder columns)
        df = df.dropna(axis=1, how='all')

        # Display the interactive table, using the correct 'width' parameter
        st.dataframe(df, width='stretch')
        
        # Offer option to download the clean table as a CSV
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Clean Data as CSV",
            data=csv_data,
            file_name='parsed_bates_data_aligned.csv',
            mime='text/csv',
        )
    elif df is not None and df.empty:
        st.warning("The file was processed, but no data rows were found.")
