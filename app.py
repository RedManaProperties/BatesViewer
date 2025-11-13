import streamlit as st
import pandas as pd
from io import StringIO

# The delimiter used in your Bates file format
DELIMITER = 'þ'

def parse_bates_file(uploaded_file):
    """Reads the uploaded .dat file, processes it, and returns a DataFrame."""
    try:
        # Read the uploaded file content into a string
        string_data = StringIO(uploaded_file.getvalue().decode('utf-8')).read()
        
        # Split the entire string by the delimiter and filter out empty strings
        data_rows = [row.strip() for row in string_data.split('\n') if row.strip()]

        # The header is the first data row (columns separated by 'þ')
        # We need to split, filter empty elements, and strip whitespace from column names
        header = [col.strip() for col in data_rows[0].split(DELIMITER) if col.strip()]

        # Process the rest of the rows
        parsed_data = []
        for line in data_rows[1:]:
            # Split by the delimiter
            row_data = line.split(DELIMITER)
            
            # Clean up the elements: strip whitespace and filter empty strings
            cleaned_row = [item.strip() for item in row_data if item.strip()]
            
            # Pad the row with empty strings if it's shorter than the header
            while len(cleaned_row) < len(header):
                cleaned_row.append("")

            # Truncate the row if it's longer than the header (handles stray delimiters at the end)
            if len(cleaned_row) > len(header):
                cleaned_row = cleaned_row[:len(header)]
            
            # Ensure the row has the exact number of columns as the header
            if len(cleaned_row) == len(header):
                parsed_data.append(cleaned_row)

        # Create the DataFrame
        df = pd.DataFrame(parsed_data, columns=header)
        
        # Clean up column names (remove the 'þ' wrapping, if present)
        df.columns = [col.strip(DELIMITER) for col in df.columns]

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
        
        # Convert columns to appropriate types where possible
        if 'Pages' in df.columns:
            # Attempt to convert 'Pages' column to numeric, coercing errors to NaN
            df['Pages'] = pd.to_numeric(df['Pages'], errors='coerce').fillna('N/A').astype(object)
            
        # Display the interactive table
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
