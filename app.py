import streamlit as st
import pandas as pd
from io import StringIO

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
    # This header spanned two lines in the original file source, which is why parsing broke
    'Original Folder Path', 
    'MD5 Hash', 
    'Parent Document ID', 
    'Document Title', 
    'Time Zone', 
    'Text Link', 
    'Native Link' 
    # The actual file provided seems to have 28, 29 or 31 fields depending on parsing method
    # Sticking to the most important metadata fields visible in the original text structure:
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
        # This regex replaces the pattern "þ[spaces]þ" with "TAB".
        cleaned_content = re.sub(r'þ\s*þ', '\t', file_content)

        # Remove the first/last delimiters and any trailing spaces/tabs
        cleaned_content = cleaned_content.strip(DELIMITER).strip()

        # 2. Re-read into pandas using the cleaned content and known headers
        # We use a space as the delimiter since the original delimiter was removed.
        # And let the parser split the rows by tabs created above.
        data = StringIO(cleaned_content)
        
        df = pd.read_csv(
            data,
            sep='\t', 
            engine='python',
            # Skip the header rows (first 3 lines in the source document)
            skiprows=[0, 1, 2],
            # Do not allow pandas to infer headers; we supply them later
            header=None,
            # Handle empty lines that might still be present
            skip_blank_lines=True
        )

        # 3. Assign the correct, pre-defined headers
        # We need to manually check how many data columns we actually got
        num_columns = df.shape[1]
        
        # The true headers are located in the last few rows of the original file (rows 0, 1, 2).
        # To simplify, we will manually define them and trim/expand to match the data length.
        
        # The definitive list based on 31 expected columns (including the 3 empty columns for attachments metadata)
        master_headers = [
            'Bates Begin', 'Bates End', 'Bates Begin Attach', 'Bates End Attach', 
            'Attachment Document', 'Pages', 'Author', 'Custodian/Source', 
            'Date Created', 'Date Last Modified', 'Date Received', 'Date Sent', 
            'Time Sent', 'Document Extension', 'Email BCC', 'Email CC', 
            'Email From', 'Email Subject/Title', 'Email To', 'Original Filename', 
            'File Size', 'Original Folder Path', 'MD5 Hash', 'Parent Document ID', 
            'Document Title', 'Time Zone', 'Text Link', 'Native Link', 
            # Placeholders for any unexpected columns if present in data
            'Col_29', 'Col_30', 'Col_31'
        ]

        # Use only the necessary headers, then rename them based on the best fit:
        df.columns = master_headers[:num_columns]
        
        return df.iloc[:, :len(DEFINITIVE_HEADERS)] # Select only the definitive columns

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
    df = clean_and_load_data(uploaded_file)

    if df is not None and not df.empty:
        st.success("File successfully parsed and loaded! The column order is now forced to match the expected format.")
        
        # Data Cleaning for Presentation
        if 'Pages' in df.columns:
            # Convert 'Pages' to numeric, filling non-numeric with empty string
            df['Pages'] = pd.to_numeric(df['Pages'], errors='coerce').fillna('').astype(object)
            
        # Drop columns that are empty (e.g., original empty attachment metadata fields)
        df = df.dropna(axis=1, how='all')

        # Display the interactive table, fixing the deprecation warning
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
