import streamlit as st
import pandas as pd
from io import StringIO
import re  # 

# The delimiter used in your Bates file format
DELIMITER = 'þ'

# The definitive list of 31 column headers, in the correct order,
# based on the standard Bates file specification.
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
    Reads the file, standardizes delimiters, and loads into a DataFrame 
    using the definitive column headers.
    """
    try:
        # Read the file content as a single string
        file_content = uploaded_file.getvalue().decode('utf-8')
        
        # 1. Clean data of unwanted characters and replace the messy delimiter pattern
        # Remove BOM and non-standard separator \x14
        file_content = file_content.lstrip('\ufeff').replace('\x14', '')
        
        # Replace the multiple-space-separated delimiter pattern (þ...þ ... þ) 
        # with a simple single tab character for robust CSV reading.
        cleaned_content = re.sub(r'þ\s*þ', '\t', file_content)

        # Remove the first/last delimiters and any trailing spaces/tabs
        cleaned_content = cleaned_content.strip(DELIMITER).strip()

        # 2. Re-read into pandas using the cleaned content and known headers
        data = StringIO(cleaned_content)
        
        # Manually parse the header from the first part of the original file content
        header_raw_lines = [line.strip() for line in file_content.split('\n') if line.strip()][:3]
        header_text = "".join(header_raw_lines)
        header_text = header_text.replace('Original \nFolder Path', 'Original Folder Path')
        
        raw_header_parts = [p.strip() for p in header_text.split(DELIMITER)]
        current_headers = [p for p in raw_header_parts if p and not p.isspace()]
        
        # Determine how many columns of data we need to extract from the cleaned content
        expected_cols_to_read = len(current_headers)

        # 3. Load data with pd.read_csv using a tab as separator
        # We start reading data from the 4th line (index 3) since the header spanned multiple lines
        # and we only provided the clean content that starts right after the header.
        df = pd.read_csv(
            data,
            sep='\t', 
            engine='python',
            # Skip the rows containing the original headers (index 0, 1, 2)
            skiprows=[0, 1, 2],
            header=None,
            skip_blank_lines=True
        )

        # 4. Assign the correct, pre-defined headers and trim extraneous columns
        
        # Only take data columns up to the number of columns found in the definitive list
        df = df.iloc[:, :len(DEFINITIVE_HEADERS)]
        df.columns = DEFINITIVE_HEADERS[:df.shape[1]]

        return df

    except Exception as e:
        st.error(f"An unexpected error occurred during parsing: {e}")
        # Optionally print full error for debugging in the console
        # st.exception(e)
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
        st.success("File successfully parsed and loaded! The column order is now forced to match the expected format.")
        
        # Data Cleaning for Presentation
        if 'Pages' in df.columns:
            # Convert 'Pages' to numeric, filling non-numeric with empty string
            df['Pages'] = pd.to_numeric(df['Pages'], errors='coerce').fillna('').astype(object)
            
        # Drop columns that are entirely empty (common in Bates load files)
        df = df.dropna(axis=1, how='all')

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
