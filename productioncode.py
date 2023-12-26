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
    st.write("Credentials loaded successfully.")

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
    st.title("Patch Cord Production App")

    # Calculate the date seven days ago
    today_minus_7_days = pd.to_datetime('today') - pd.DateOffset(days=7)

    # Assuming 'Date' is a column in your DataFrame
    df['Date'] = pd.to_datetime(df['Date'])

    # Set pandas options to display all columns and expand the width of the 'Steps' column
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_colwidth', None)

    # Display data for the last 7 days
    st.markdown("<h1 style='text-align: center;'>Data from Production (Last 7 Days)</h1>", unsafe_allow_html=True)
    last_7_days_data = df[df['Date'] >= today_minus_7_days]
    st.write(last_7_days_data)

    # Warning Section
    st.markdown("<h1 style='text-align: center;'>Warning Section</h1>", unsafe_allow_html=True)

    # Convert 'Mistake_rates' column to numeric, handling errors with coerce
    df['Mistake_rates'] = pd.to_numeric(df['Mistake_rates'], errors='coerce')

    # Identify abnormal rows based on mistake rates
    abnormal_rows = df['Mistake_rates'].ge(0.02) & ~df['Mistake_rates'].isna()

    # Count the number of abnormal rows for each threshold
    abnormal_counts = []

    for threshold in np.arange(0.02, 0.10, 0.01):
        count = abnormal_rows[(df['Mistake_rates'] >= threshold) & (df['Mistake_rates'] < threshold + 0.01)].sum()
        abnormal_counts.append({"Threshold": f"{threshold:.2f} - {threshold + 0.01:.2f}", "Count": count})

    # Count of Rows with Mistake Rates >= 0.10
    count_high_mistake_rates = abnormal_rows[df['Mistake_rates'] >= 0.10].sum()
    abnormal_counts.append({"Threshold": ">= 0.10", "Count": count_high_mistake_rates})

    # Display the results in an organized table
    st.subheader("Count of Rows with Mistake Rates")
    abnormal_table = pd.DataFrame(abnormal_counts)
    st.table(abnormal_table)
        
    # Function to calculate the total of abnormal (mistakes >=0.020)
    total_abnormal = abnormal_rows.sum()
    st.subheader("Total Abnormal Rows (Mistake Rates >= 0.020)")
    st.write(f"Total abnormal rows: {total_abnormal}")

    # Display details if there are abnormal rows
    if abnormal_rows.any():
        # Toggle button to show/hide details
        details_button = st.button("Toggle Details of Rows with Abnormal Mistake Rates")
    
        if details_button:
             st.warning("Details of Rows with Abnormal Mistake Rates:")
             abnormal_rows_details = df[abnormal_rows]
             st.write(abnormal_rows_details)
    else:
        st.success("No abnormal rows found in the dataset.")


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
    st.markdown("<h1 style='text-align: center;'>Total Time/person</h1>", unsafe_allow_html=True)
    st.write(result_df)
else:
    st.error("Unable to load data from Google Drive.")

# Reset pandas options to their default values after displaying the DataFrames
pd.reset_option('display.max_columns')
pd.reset_option('display.max_colwidth')
