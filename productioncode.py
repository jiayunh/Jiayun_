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

    # Warning Section
    st.markdown("<h1 style='text-align: center;'>不良率详情</h1>", unsafe_allow_html=True)

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

    # Function to calculate the total of abnormal (mistakes >=0.020)
    total_abnormal = abnormal_rows.sum()
    abnormal_counts.append({"Threshold": "Total Abnormal", "Count":total_abnormal})
    
    # Display the results in an organized table
    st.subheader("不良率统计")
    abnormal_table = pd.DataFrame(abnormal_counts)
    st.table(abnormal_table)
        

    # Display details if there are abnormal rows
    if abnormal_rows.any():
        # Toggle button to show/hide details
        details_button = st.button("点击查看详情")
    
        if details_button:
             st.warning("Details of Rows with Abnormal Mistake Rates:")
             abnormal_rows_details = df[abnormal_rows]
             abnormal_rows_details['Date'] = abnormal_rows_details['Date'].dt.strftime('%Y-%m-%d')
             abnormal_rows_details['Order_number'] = abnormal_rows_details['Order_number'].astype(int)
             st.write(abnormal_rows_details)
    else:
        st.success("No abnormal rows found in the dataset.")

    #Filter Data 1
    st.sidebar.title("选取生产数据")

    # Add a selectbox for month and year filtering
    selected_month = st.sidebar.selectbox("选择月份", range(1, 13), format_func=lambda x: f"{x:02d}")  # Format month with leading zero
    selected_year = st.sidebar.selectbox("选择年份", range(2023, 2025))

    #Filter the DataFrame based on selected month and year
    filtered_by_date_df = df[
    (df['Date'].dt.month == int(selected_month)) & (df['Date'].dt.year == int(selected_year))
    ]   
    filtered_by_date_df['Date'] = filtered_by_date_df['Date'].dt.strftime('%Y-%m-%d')
    filtered_by_date_df['Order_number'] = filtered_by_date_df['Order_number'].astype(int)
    
    if st.sidebar.button("按日期过滤"):
    # Display the filtered DataFrame
       st.subheader("按日期过滤结果")
       st.write(filtered_by_date_df)
    
    
    # Filter Data Section 2
    st.sidebar.title("选择跳线数据")
    cable_type = st.sidebar.selectbox("选择跳线种类", [''] + sorted(df['Type'].unique().tolist()))
    color = st.sidebar.selectbox("选择颜色", [''] + sorted(df['Color'].astype(str).unique().tolist()))
    length = st.sidebar.selectbox("选择长度", [''] + sorted(df['Length'].astype(str).unique().tolist()))

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

    if st.sidebar.button("获取筛选数据结果"):
        filtered_df = filter_data(df, cable_type, length, color)
        filtered_df['Date'] = filtered_df['Date'].dt.strftime('%Y-%m-%d')
        filtered_df['Order_number'] = filtered_df['Order_number'].astype(int)
        st.subheader(f"{cable_type}, {length}, {color} 筛选数据展示")
        st.write(filtered_df)
        

        if filtered_df.empty:
            st.info("No matching entries.")


    # Results Section

    # Convert "Total_time" and "Time_per_person" to numeric
    df["Time_per_person"] = pd.to_numeric(df["Time_per_person"], errors="coerce")
    df["Total_time"]=pd.to_numeric(df["Total_time"], errors="coerce")

    # Group by Type, Color, and Length
    grouped_df = df.groupby(["Type", "Color", "Length", "Order_number"])

    # Store the results in a list of tables
    tables = []

    # Display the results
    for name, group in grouped_df:
        total_time_per_person = group["Time_per_person"].sum()
        total_production_time=group["Total_time"].sum()
        last_step = group.iloc[-1]["End_Steps"]
        date=group.iloc[-1]["Date"]
        
        # Add data to the table
        result_table = {
            "Date":date,
            "Type": name[0],
            "Color": name[1],
            "Length": name[2],
            "Order_number": name[3],
            "Total_time_per_person": total_time_per_person,
            "Total_production_time": total_production_time,
            "Last_step": last_step
        }

        # Append the result table to the list
        tables.append(result_table)

    # Convert the list of tables to a DataFrame
    result_df = pd.DataFrame(tables)
    result_df['Date'] = result_df['Date'].dt.strftime('%Y-%m-%d')
    result_df['Order_number'] = result_df['Order_number'].astype(int)
   

   # Display the final DataFrame
    st.markdown("<h1 style='text-align: center;'>生产工时详情</h1>", unsafe_allow_html=True)
    st.write(result_df)   

    # Add a filter button
    if st.button("已装箱入库"):
       # Filter and sort the DataFrame
       filtered_df = result_df[result_df['Last_step'].str.contains('storage', case=False, na=False)].sort_values(by='Date')
       
        
       # Display the filtered DataFrame
       st.markdown("<h2 style='text-align: center;'>已装箱入库结果</h2>", unsafe_allow_html=True)
       st.write(filtered_df)

    # Add a filter button for 'Non storage' (does not contain 'storage')
    if st.button("未装箱入库"):
    # Filter and sort the DataFrame
       non_storage_df = result_df[~result_df['Last_step'].str.contains('storage', case=False, na=False)].sort_values(by='Date')
       
       # Display the filtered DataFrame
       st.markdown("<h2 style='text-align: center;'>非装箱入库结果</h2>", unsafe_allow_html=True)
       st.write(non_storage_df)

else:
    st.error("Unable to load data from Google Drive.")

# Reset pandas options to their default values after displaying the DataFrames
pd.reset_option('display.max_columns')
pd.reset_option('display.max_colwidth')
