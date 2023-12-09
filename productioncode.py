import streamlit as st
import pandas as pd
import os
import toml
from google.oauth2 import service_account
from googleapiclient.discovery import build
from io import BytesIO


import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Define credentials with an initial value of None
credentials = None

try:
    credentials = service_account.Credentials.from_service_account_info(
        credentials_dict,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    st.write("Credentials loaded successfully.")
except Exception as e:
    st.error(f"Error loading credentials: {e}")

# Check if credentials is not None before building the drive_service
if credentials:
    # Build the Google Drive API service
    drive_service = build('drive', 'v3', credentials=credentials)
else:
    st.error("Credentials not available. Unable to build drive_service.")


# Function to read the contents of the specified file
def read_drive_file(file_name):
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
file_name = "production.csv"  # assuming this is your file name
file_content = read_drive_file(file_name)

# If file content is available, display it as a DataFrame
if file_content:
    df = pd.read_csv(BytesIO(file_content))

    # Display data in Streamlit app
    st.title("Patch Cord Production App")

    # Calculate the date seven days ago
    today_minus_7_days = pd.to_datetime('today') - pd.DateOffset(days=7)

    # Assuming 'Date' is a column in your DataFrame
    df['Date'] = pd.to_datetime(df['Date'])

    # Display data for the last 7 days
    st.header("Data from Production (Last 7 Days)")
    last_7_days_data = df[df['Date'] >= today_minus_7_days]
    st.write(last_7_days_data)

    # Filter Data Section
    st.sidebar.title("Filter Data")
    cable_type = st.sidebar.selectbox("Select Cable Type", [''] + sorted(df['Type'].unique().tolist()))
    color = st.sidebar.selectbox("Select Color", [''] + sorted(df['Color'].astype(str).unique().tolist()))
    length = st.sidebar.selectbox("Select Length", [''] + sorted(df['Length'].astype(str).unique().tolist()))

    def filter_data(df, cable_type=None, length=None, color=None):
        filtered_data = df.copy()

        if cable_type:
            filtered_data = filtered_data[filtered_data['Type'] == cable_type]
        if length:
            filtered_data = filtered_data[filtered_data['Length'].astype(str) == length]
        if color:
            color = color.lower()  # Convert user input to lowercase
            filtered_data = filtered_data[filtered_data['Color'].astype(str).str.lower() == color]

        return filtered_data

    if st.sidebar.button("Filter Data"):
        filtered_df = filter_data(df, cable_type, length, color)
        st.subheader("Filtered Data")
        st.write(filtered_df)
        
        if filtered_df.empty:
            st.info("No matching entries.")

    # Results Section
    st.sidebar.title("Results")

    # Convert "Total_time" and "Time_per_person" to numeric
    df["Total_time"] = pd.to_numeric(df["Total_time"], errors="coerce")
    df["Time_per_person"] = pd.to_numeric(df["Time_per_person"], errors="coerce")

    # Group by Type, Color, and Length
    grouped_df = df.groupby(["Type", "Color", "Length"])

    # Store the results in a list of tables
    tables = []

    # Display the results
    for name, group in grouped_df:
        total_time_per_person = group["Time_per_person"].sum()
        last_step = group.iloc[-1]["Steps"]
        
        # Add data to the table
        result_table = {
            "Type": name[0],
            "Color": name[1],
            "Length": name[2],
            "Total_time_per_person": total_time_per_person,
            "Last_step": last_step,
        }
        
        # Append the result table to the list
        tables.append(result_table)

    # Convert the list of tables to a DataFrame
    result_df = pd.DataFrame(tables)

    # Display the final DataFrame
    st.subheader("Total Time/person")
    st.write(result_df)
else:
    st.error("Unable to load data from Google Drive.")











