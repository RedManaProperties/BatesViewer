import streamlit as st
import pandas as pd
from io import StringIO
import re
import csv
import string
import os

# --- Configuration ---
# Set the default filename for automatic loading
FIXED_FILENAME = 'HOUSE_OVERSIGHT_009.dat'
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

def generate_column_names(n):
    """Generates column names A, B, C, ..., AA, AB, etc."""
    names = []
    for i in range(n):
        name = ""
        temp_i = i
        while temp_i >= 0:
            name = string.ascii_uppercase[temp_i % 26] + name
            temp_i = temp_i // 26 - 1
        names.append(name)
    return names

def parse_data_from_content(file_content, use_fixed_headers=False):
    """
    Parses the content line-by-line using the csv module to split, 
    and handles dynamic vs. fixed headers.
    """
    # Remove Byte Order Mark (BOM) and non-standard separator \x14 globally
    file_content = file_content.lstrip('\ufeff').replace('\x14', '')
    
    lines = file_content.split('\n')
    
    # Find the start of the actual data rows
    data_start_index = 0
    for i, line in enumerate(lines):
        if 'Native Link' in line:
            data_start_index = i + 1
            break
            
    # Process only the data lines
    raw_data_lines = lines[data_start_index:]
    parsed_data = []
    max_cols = 0
    
    # Use csv.reader for reliable splitting based on the delimiter
    reader = csv.reader(raw_data_lines, delimiter=DELIMITER)
    
    for row_values in reader:
        if not row_values:
            continue
            
        cleaned_row = [v.strip() for v in row_values]
        
        # Remove empty strings that result from the leading and trailing delimiter
        if cleaned_row and cleaned_row[0] == '':
            cleaned_row.pop(0)
        if cleaned_row and cleaned_row[-1] == '':
            cleaned_row.pop(-1)
        
        # Track the widest row
        max_cols = max(max_cols, len(cleaned_row))
        parsed_data.append(cleaned_row)

    if max_cols == 0 and parsed_data:
        raise Exception("Failed to extract meaningful columns from data rows.")
    elif max_cols == 0 and not parsed_data:
        return pd.DataFrame()

    # Standardize and pad all rows to the maximum width observed
    for row in parsed_data:
        if len(row) < max_cols:
            row.extend([""] * (max_cols - len(row)))
        elif len(row) > max_cols:
            row[:] = row[:max_cols]

    # Create headers based on the desired mode
    if use_fixed_headers and max_cols <= len(DEFINITIVE_HEADERS):
        headers_to_use = DEFINITIVE_HEADERS[:max_cols]
    else:
        # Fallback to generic headers if the length is unexpected or fixed headers aren't used
        headers_to_use = generate_column_names(max_cols)

    # Create the DataFrame
    df = pd.DataFrame(parsed_data, columns=headers_to_use)
    
    # Post-processing clean-up
    if 'Pages' in df.columns:
        df['Pages'] = pd.to_numeric(df['Pages'], errors='coerce').fillna('').astype(object)
    
    # Drop columns that are entirely empty across all rows 
    df = df.dropna(axis=1, how='all')
    
    return df

def main():
    st.set_page_config(layout="wide")
    st.title("📂 Bates File Viewer (Epstein Documents Index)")
    
    # --- New Information Note ---
    st.info(
        "📰 This viewer was created by Radio Free Hub City is set to automatically load the **latest Epstein file index in Bates format**, released on **11/12/2025**. "
        "This table provides **metadata only**. To view the actual document files, find the corresponding filename in the table "
        "and access the full release here: [https://oversight.house.gov/release/oversight-committee-releases-additional-epstein-estate-documents/](https://oversight.house.gov/release/oversight-committee-releases-additional-epstein-estate-documents/)"
        "-"
        "To view our latest coverage on this and other local and national news, visit [https://radiofreehubcity.com](https://radiofreehubcity.com)"
    )
    # ----------------------------

    df = None
    source_info = ""

    # 1. Try to automatically load the local file
    file_path = os.path.join(os.getcwd(), FIXED_FILENAME)
    
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # Use fixed headers for the known file
            df = parse_data_from_content(file_content, use_fixed_headers=True)
            source_info = f"**Currently loaded:** `{FIXED_FILENAME}` (from local directory)."
            
        except Exception as e:
            st.warning(f"⚠️ Auto-load failed for `{FIXED_FILENAME}`. Error: {e}")
            st.info("The local file could not be parsed correctly. Please try uploading a file below.")

    # 2. File Uploader for override or initial load if auto-load failed
    uploaded_file = st.sidebar.file_uploader("Upload an alternative .dat or delimited file", type=['dat', 'txt', 'csv'])

    if uploaded_file is not None:
        # If a file is uploaded, use it instead (and use generic headers for safety)
        file_content_upload = uploaded_file.getvalue().decode('utf-8')
        df = parse_data_from_content(file_content_upload, use_fixed_headers=False)
        source_info = f"**Currently loaded:** `{uploaded_file.name}` (uploaded). Headers use generic letters for guaranteed alignment."

    # --- Display Results ---
    if df is not None and not df.empty:
        st.markdown(source_info)
        st.success(f"File parsed and loaded with {df.shape[1]} columns. ")
        
        # Display the interactive table
        st.dataframe(df, width='stretch')
        
        # Offer download option
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Clean Data as CSV",
            data=csv_data,
            file_name='parsed_bates_data_aligned.csv',
            mime='text/csv',
        )
    elif os.path.exists(file_path) and df is None:
        # Display message if local file exists but failed to parse and no upload happened
        st.warning(f"Could not parse `{FIXED_FILENAME}`. Please try uploading a file in the sidebar.")
    else:
        st.info("Please upload a Bates `.dat` file using the sidebar uploader to begin analysis.")

if __name__ == '__main__':
    main()
