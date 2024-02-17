import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from io import BytesIO
import numpy as np

# Retrieve credentials from Streamlit secrets
credentials_dict = st.secrets["google_drive_credentials"]

try:
    credentials = service_account.Credentials.from_service_account_info(
        credentials_dict,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    st.write("欢迎")

    # Build the Google Drive API service
    drive_service = build('drive', 'v3', credentials=credentials)
except Exception as e:
    st.error(f"Error loading credentials: {e}")
    drive_service = None

# Function to read the contents of the specified file
def read_drive_file(file_name):
    if drive_service is None:
        st.error("Drive service is not available.")
        return None

    results = drive_service.files().list(
        q=f"name='{file_name}'", pageSize=1, fields="files(id, name)"
    ).execute()

    items = results.get('files', [])
    if not items:
        st.error(f"File '{file_name}' not found in Google Drive.")
        return None

    file_id = items[0]['id']
    request = drive_service.files().get_media(fileId=file_id)
    file_content = request.execute()

    return file_content

# Read the contents of "production.csv"
file_name = "production.csv"
file_content = read_drive_file(file_name)

# If file content is available, display it as a DataFrame
if file_content:
    df = pd.read_csv(BytesIO(file_content))

    # Display data in Streamlit app    
    st.markdown(
    """<h1 style='text-align: center; color: royalblue;'>跳线生产分析</h1>""",
    unsafe_allow_html=True
    )

    # Calculate the date seven days ago
    today_minus_7_days = pd.to_datetime('today') - pd.DateOffset(days=7)

    # Assuming 'Date' is a column in your DataFrame
    df['Date'] = pd.to_datetime(df['Date'])

    # Set pandas options to display all columns and expand the width of the 'Steps' column
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_colwidth', None)

    # Display data for the last 7 days
    st.markdown("<h1 style='text-align: center;'>过去一周的跳线生产表格</h1>", unsafe_allow_html=True)
    last_7_days_data = df[df['Date'] >= today_minus_7_days]
    last_7_days_data['Date'] = last_7_days_data['Date'].dt.strftime('%Y-%m-%d')
    last_7_days_data['Order_number'] = last_7_days_data['Order_number'].astype(int)
    st.write(last_7_days_data)
