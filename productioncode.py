import streamlit as st
import dropbox
import pandas as pd
from tabulate import tabulate

# Dropbox access token
ACCESS_TOKEN = 'sl.BrawQJfbrHOQOCO2CXNN9GrGCWuHxufbyhhaW8ncG9_Zs1yvCFON7HQxHFXrzWnAp2x8yId1uSHEP6T8VVBxW794q11X-Lr5COU1IQyy-h1W9xIkCf_SEtm1QS8udBBwjywTxI623F0qBjfEVytUu54'
# Dropbox file path
DROPBOX_FILE_PATH = '/production.csv'

# Connect to Dropbox and download the file
dbx = dropbox.Dropbox(ACCESS_TOKEN)

with st.spinner("Downloading data from Dropbox..."):
    metadata, res = dbx.files_download(DROPBOX_FILE_PATH)
    with open('production.csv', 'wb') as f:
        f.write(res.content)

# Read data from the local file
df = pd.read_csv('production.csv')

# Display data in Streamlit app
st.title("Patch Cord Production App")

# Calculate the date seven days ago
today_minus_7_days = pd.to_datetime('today') - pd.DateOffset(days=7)

# Print the date and its type
print(f"Date of 'today_minus_7_days': {today_minus_7_days}")
print(f"Type of 'today_minus_7_days': {type(today_minus_7_days)}")

# Assuming 'Date' is a column in your DataFrame
df['Date'] = pd.to_datetime(df['Date'])

# Debugging output
date_column_dtype = df['Date'].dtype
print(f"Data type of 'Date' column: {date_column_dtype}")

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


