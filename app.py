import streamlit as st
import pandas as pd
from io import StringIO
import re

# The delimiter used in your Bates file format
DELIMITER = 'þ'

def parse_bates_file(uploaded_file):
    """
    Reads the uploaded file, manually parses the delimited data, 
    cleans up headers and rows, and returns a DataFrame.
    """
    try:
        # Read the file content as a single string
        file_content = uploaded_file.getvalue().decode('utf-8')
        
        # Remove Byte Order Mark (BOM) and non-standard field separator (\x14)
        file_content = file_content.lstrip('\ufeff').replace('\x14', '')
        
        # Split into lines
        lines = file_content.split('\n')
        # Filter out purely empty lines
        data_lines = [line.strip() for line in lines if line.strip()]

        if not data_lines:
            return pd.DataFrame()

        # 1. Process Header
        # Determine the header lines (assuming it's the first few lines until 'Native Link' is seen)
        header_end_index = 0
        for i, line in enumerate(data_lines):
            # We look for the last column name, 'Native Link'
            if 'Native Link' in line:
                header_end_index = i
                break
        
        # Join header lines (handling the multiline column name "Original Folder Path")
        header_text = "".join(data_lines[:header_end_index + 1])
        
        # Clean up the known multi-line header issue
        header_text = header_text.replace('Original \nFolder Path', 'Original Folder Path')

        # Split by the delimiter 'þ'. The structure is 'þCol1þ þCol2þ...', 
        # so splitting creates an empty string at the start and around the ' þ' separators.
        raw_header_parts = [p.strip() for p in header_text.split(DELIMITER)]
        
        # Filter out empty strings and strings consisting only of spaces, which are the separators.
        header = [p for p in raw_header_parts if p and not p.isspace()]
        
        # 2. Process Data Rows
        parsed_data = []
        expected_len = len(header)
        
        for line in data_lines[header_end_index + 1:]:
            # Split by delimiter. Rows start with 'þ' so splitting yields ['', 'Val1', 'Val2', ...]
            row_values = [v.strip() for v in line.split(DELIMITER)]
            
            # Remove leading/trailing empty strings from the row split
            if row_values and row_values[0] == '':
                row_values.pop(0)
            if row_values and row_values[-1] == '':
                row_values.pop(-1)

            # Clean any remaining spaces/control chars and ensure length matches header
            current_len = len(row_values)
            
            if current_len > expected_len:
                row_values = row_values[:expected_len]
            elif current_len < expected_len:
                row_values.extend([""] * (expected_len - current_len))

            if len(row_values) == expected_len:
                parsed_data.append(row_values)

        # Create DataFrame
        df = pd.DataFrame(parsed_data, columns=header)
        
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
    df = parse_bates_file(uploaded_file)

    if df is not None and not df.empty:
        st.success("File successfully parsed and loaded! The table columns have been properly identified.")
        
        # Convert 'Pages' column to numeric for better sorting/display, coercing errors
        if 'Pages' in df.columns:
            df['Pages'] = pd.to_numeric(df['Pages'], errors='coerce').fillna('').astype(object)
            
        # Display the interactive table, using the updated 'width' parameter
        # to fix the deprecation warning/error:
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
