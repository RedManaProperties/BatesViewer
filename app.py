import streamlit as st
import pandas as pd
from io import StringIO

# The delimiter used in your Bates file format
DELIMITER = 'þ'

def parse_bates_file(uploaded_file):
    """
    Reads the uploaded file using a robust method to handle the delimiter,
    cleans up column names (removes BOM and surrounding delimiters),
    and returns a DataFrame.
    """
    try:
        # Read the file content and replace multiple delimiters with a single one
        file_content = uploaded_file.getvalue().decode('utf-8')
        
        # Replace the Windows Byte Order Mark (BOM) if present, as it can cause duplicate columns
        file_content = file_content.lstrip('\ufeff')

        # Since the field names and values are enclosed in 'þ' and separated by it,
        # we can't use the regular CSV reader that expects fields separated by commas/tabs.
        # We need to manually split and strip.
        
        # Split into lines
        lines = file_content.split('\n')
        
        # Filter out empty lines
        data_lines = [line.strip() for line in lines if line.strip()]

        if not data_lines:
            return pd.DataFrame()

        # The raw header is the first line
        raw_header = data_lines[0]
        
        # Split by the delimiter 'þ', keep all parts (including empty ones for blank columns)
        # Remove empty strings at the start/end from the split operation
        raw_columns = [col.strip() for col in raw_header.split(DELIMITER)]
        if raw_columns[0] == '':
            raw_columns.pop(0)
        if raw_columns[-1] == '':
            raw_columns.pop(-1)
        
        # The cleaned header names are the raw column names stripped of extra control characters
        # The original problem was from internal tool characters, not the surrounding 'þ'
        header = [col.strip() for col in raw_columns]

        # Process data rows
        parsed_data = []
        for line in data_lines[1:]:
            # Split by delimiter, remove empty strings at the start/end from the split operation
            row_values = [v.strip() for v in line.split(DELIMITER)]
            if row_values[0] == '':
                row_values.pop(0)
            if row_values[-1] == '':
                row_values.pop(-1)
            
            # Pad or truncate to match the expected number of columns for robustness
            if len(row_values) > len(header):
                row_values = row_values[:len(header)]
            elif len(row_values) < len(header):
                row_values.extend([""] * (len(header) - len(row_values)))
            
            if len(row_values) == len(header):
                # Replace the problematic control character '\x14' with an empty string or strip it
                cleaned_row = [v.replace('\x14', '').strip() for v in row_values]
                parsed_data.append(cleaned_row)

        # Create the DataFrame
        df = pd.DataFrame(parsed_data, columns=header)
        
        # Clean up column names (remove all remaining control characters or spaces)
        df.columns = [c.replace('\x14', '').strip() for c in df.columns]

        return df

    except Exception as e:
        st.error(f"Error processing file: {e}")
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
        st.success("File successfully parsed and loaded!")
        
        # Convert 'Pages' column to numeric, coercing errors to an appropriate format
        if 'Pages' in df.columns:
            # Errors='coerce' turns invalid parsing into NaN, fillna replaces NaN with 'N/A'
            df['Pages'] = pd.to_numeric(df['Pages'], errors='coerce').fillna('N/A').astype(object)
            
        # Display the interactive table, fixing the deprecation warning
        st.dataframe(df, use_container_width=True)
        
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
